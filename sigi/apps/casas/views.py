# -*- coding: utf-8 -*-
import csv
from functools import reduce

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _, ungettext
from geraldo.generators import PDFGenerator

from sigi.apps.casas.models import CasaLegislativa
from sigi.apps.casas.reports import CasasLegislativasLabels, CasasLegislativasLabelsSemPresidente, CasasLegislativasReport, CasasSemConvenioReport, InfoCasaLegislativa
from sigi.apps.parlamentares.reports import ParlamentaresLabels
from sigi.apps.contatos.models import UnidadeFederativa, Mesorregiao, Microrregiao
from sigi.apps.casas.forms import PortfolioForm


# @param qs: queryset
# @param o: (int) number of order field


def query_ordena(qs, o):
    from sigi.apps.casas.admin import CasaLegislativaAdmin
    list_display = CasaLegislativaAdmin.list_display
    order_fields = []

    for order_number in o.split('.'):
        order_number = int(order_number)
        order = ''
        if order_number != abs(order_number):
            order_number = abs(order_number)
            order = '-'
        order_fields.append(order + list_display[order_number - 1])

    qs = qs.order_by(*order_fields)
    return qs


def get_for_qs(get, qs):
    """
        Verifica atributos do GET e retorna queryset correspondente
    """
    kwargs = {}
    for k, v in get.iteritems():
        if str(k) not in ('page', 'pop', 'q', '_popup', 'o', 'ot'):
            kwargs[str(k)] = v

    qs = qs.filter(**kwargs)
    if 'o' in get:
        qs = query_ordena(qs, get['o'])

    return qs


def carrinhoOrGet_for_qs(request):
    """
       Verifica se existe casas na sessão se não verifica get e retorna qs correspondente.
    """
    if 'carrinho_casas' in request.session:
        ids = request.session['carrinho_casas']
        qs = CasaLegislativa.objects.filter(pk__in=ids)
    else:
        qs = CasaLegislativa.objects.all()
        if request.GET:
            qs = get_for_qs(request.GET, qs)
    return qs


def adicionar_casas_carrinho(request, queryset=None, id=None):
    if request.method == 'POST':
        ids_selecionados = request.POST.getlist('_selected_action')
        if 'carrinho_casas' not in request.session:
            request.session['carrinho_casas'] = ids_selecionados
        else:
            lista = request.session['carrinho_casas']
            # Verifica se id já não está adicionado
            for id in ids_selecionados:
                if id not in lista:
                    lista.append(id)
            request.session['carrinho_casas'] = lista


def visualizar_carrinho(request):

    qs = carrinhoOrGet_for_qs(request)

    paginator = Paginator(qs, 100)

    # Make sure page request is an int. If not, deliver first page.
    # Esteja certo de que o `page request` é um inteiro. Se não, mostre a primeira página.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # Se o page request (9999) está fora da lista, mostre a última página.
    try:
        paginas = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paginas = paginator.page(paginator.num_pages)

    carrinhoIsEmpty = not('carrinho_casas' in request.session)

    return render(
        request,
        'casas/carrinho.html',
        {
            'carIsEmpty': carrinhoIsEmpty,
            'paginas': paginas,
            'query_str': '?' + request.META['QUERY_STRING']
        }
    )


def excluir_carrinho(request):
    if 'carrinho_casas' in request.session:
        del request.session['carrinho_casas']
    return HttpResponseRedirect('.')


def deleta_itens_carrinho(request):
    if request.method == 'POST':
        ids_selecionados = request.POST.getlist('_selected_action')
        if 'carrinho_casas' in request.session:
            lista = request.session['carrinho_casas']
            for item in ids_selecionados:
                lista.remove(item)
            if lista:
                request.session['carrinho_casas'] = lista
            else:
                del lista
                del request.session['carrinho_casas']

    return HttpResponseRedirect('.')


def labels_report(request, id=None, tipo=None, formato='3x9_etiqueta'):
    """ TODO: adicionar suporte para resultado de pesquisa do admin.
    """

    if request.POST:
        if 'tipo_etiqueta' in request.POST:
            tipo = request.POST['tipo_etiqueta']
        if 'tamanho_etiqueta' in request.POST:
            formato = request.POST['tamanho_etiqueta']

    if tipo == 'sem_presidente':
        return labels_report_sem_presidente(request, id, formato)

    if id:
        qs = CasaLegislativa.objects.filter(pk=id)
    else:
        qs = carrinhoOrGet_for_qs(request)

    if not qs:
        return HttpResponseRedirect('../')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=casas.pdf'
    report = CasasLegislativasLabels(queryset=qs, formato=formato)
    report.generate_by(PDFGenerator, filename=response)

    return response


def labels_report_parlamentar(request, id=None, formato='3x9_etiqueta'):
    """ TODO: adicionar suporte para resultado de pesquisa do admin.
    """

    if request.POST:
        if 'tamanho_etiqueta' in request.POST:
            formato = request.POST['tamanho_etiqueta']

    if id:
        legislaturas = [c.legislatura_set.latest('data_inicio') for c in CasaLegislativa.objects.filter(pk__in=id, legislatura__id__isnull=False).distinct()]
        mandatos = reduce(lambda x, y: x | y, [l.mandato_set.all() for l in legislaturas])
        parlamentares = [m.parlamentar for m in mandatos]
        qs = parlamentares

    else:
        qs = carrinhoOrGet_for_parlamentar_qs(request)

    if not qs:
        return HttpResponseRedirect('../')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=casas.pdf'
    report = ParlamentaresLabels(queryset=qs, formato=formato)
    report.generate_by(PDFGenerator, filename=response)

    return response


def carrinhoOrGet_for_parlamentar_qs(request):
    """
       Verifica se existe parlamentares na sessão se não verifica get e retorna qs correspondente.
    """
    if 'carrinho_casas' in request.session:
        ids = request.session['carrinho_casas']
        legislaturas = [c.legislatura_set.latest('data_inicio') for c in CasaLegislativa.objects.filter(pk__in=ids, legislatura__id__isnull=False).distinct()]
        mandatos = reduce(lambda x, y: x | y, [l.mandato_set.all() for l in legislaturas])
        parlamentares = [m.parlamentar for m in mandatos]
        qs = parlamentares
    else:
        legislaturas = [c.legislatura_set.latest('data_inicio') for c in CasaLegislativa.objects.all().distinct()]
        mandatos = reduce(lambda x, y: x | y, [l.mandato_set.all() for l in legislaturas])
        parlamentares = [m.parlamentar for m in mandatos]
        qs = parlamentares
        if request.GET:
            qs = get_for_qs(request.GET, qs)
    return qs


def labels_report_sem_presidente(request, id=None, formato='2x5_etiqueta'):
    """ TODO: adicionar suporte para resultado de pesquisa do admin.
    """

    if id:
        qs = CasaLegislativa.objects.filter(pk=id)
    else:
        qs = carrinhoOrGet_for_qs(request)

    if not qs:
        return HttpResponseRedirect('../')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=casas.pdf'
    report = CasasLegislativasLabelsSemPresidente(queryset=qs, formato=formato)
    report.generate_by(PDFGenerator, filename=response)

    return response


def report(request, id=None, tipo=None):

    if request.POST:
        if 'tipo_relatorio' in request.POST:
            tipo = request.POST['tipo_relatorio']

    if tipo == 'completo':
        return report_complete(request, id)

    if id:
        qs = CasaLegislativa.objects.filter(pk=id)
    else:
        qs = carrinhoOrGet_for_qs(request)

    if not qs:
        return HttpResponseRedirect('../')

    # qs.order_by('municipio__uf','nome')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=casas.pdf'
    report = CasasLegislativasReport(queryset=qs)
    report.generate_by(PDFGenerator, filename=response)
    return response


def report_complete(request, id=None):

    if id:
        qs = CasaLegislativa.objects.filter(pk=id)
    else:
        qs = carrinhoOrGet_for_qs(request)

    if not qs:
        return HttpResponseRedirect('../')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=casas.pdf'

    # Gera um relatorio para cada casa e concatena os relatorios
    cont = 0
    canvas = None
    quant = qs.count()
    if quant > 1:
        for i in qs:
            cont += 1
            # queryset deve ser uma lista
            lista = (i,)
            if cont == 1:
                report = InfoCasaLegislativa(queryset=lista)
                canvas = report.generate_by(PDFGenerator, return_canvas=True, filename=response,)
            else:
                report = InfoCasaLegislativa(queryset=lista)
                if cont == quant:
                    report.generate_by(PDFGenerator, canvas=canvas)
                else:
                    canvas = report.generate_by(PDFGenerator, canvas=canvas, return_canvas=True)
    else:
        report = InfoCasaLegislativa(queryset=qs)
        report.generate_by(PDFGenerator, filename=response)

    return response

def casas_sem_convenio_report(request):
    qs = CasaLegislativa.objects.filter(convenio=None).order_by('municipio__uf', 'nome')

    if request.GET:
        qs = get_for_qs(request.GET, qs)
    if not qs:
        return HttpResponseRedirect('../')

    response = HttpResponse(content_type='application/pdf')
    report = CasasSemConvenioReport(queryset=qs)
    report.generate_by(PDFGenerator, filename=response)
    return response


def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=casas.csv'

    writer = csv.writer(response)

    casas = carrinhoOrGet_for_qs(request)
    if not casas or not request.POST:
        return HttpResponseRedirect('../')

    atributos = request.POST.getlist("itens_csv_selected")
    atributos2 = [s.encode("utf-8") for s in atributos]

    try:
        atributos2.insert(atributos2.index(_(u'Município')), _(u'UF'))
    except ValueError:
        pass

    writer.writerow(atributos2)

    for casa in casas:
        lista = []
        contatos = casa.funcionario_set.filter(setor="contato_interlegis")
        for atributo in atributos:
            if _(u"CNPJ") == atributo:
                lista.append(casa.cnpj.encode("utf-8"))
            elif _(u"Código IBGE") == atributo:
                lista.append(str(casa.municipio.codigo_ibge).encode("utf-8"))
            elif _(u"Código TSE") == atributo:
                lista.append(str(casa.municipio.codigo_tse).encode("utf-8"))
            elif _(u"Nome") == atributo:
                lista.append(casa.nome.encode("utf-8"))
            elif _(u"Município") == atributo:
                lista.append(unicode(casa.municipio.uf.sigla).encode("utf-8"))
                lista.append(unicode(casa.municipio.nome).encode("utf-8"))
            elif _(u"Presidente") == atributo:
                # TODO: Esse encode deu erro em 25/04/2012. Comentei para que o usuário pudesse continuar seu trabalho
                # É preciso descobrir o porque do erro e fazer a correção definitiva.
                #                lista.append(str(casa.presidente or "").encode("utf-8"))
                lista.append(str(casa.presidente or ""))
            elif _(u"Logradouro") == atributo:
                lista.append(casa.logradouro.encode("utf-8"))
            elif _(u"Bairro") == atributo:
                lista.append(casa.bairro.encode("utf-8"))
            elif _(u"CEP") == atributo:
                lista.append(casa.cep.encode("utf-8"))
            elif _(u"Telefone") == atributo:
                lista.append(str(casa.telefone or ""))
            elif _(u"Página web") == atributo:
                lista.append(casa.pagina_web.encode("utf-8"))
            elif _(u"Email") == atributo:
                lista.append(casa.email.encode("utf-8"))
            elif _(u"Número de parlamentares") == atributo:
                lista.append(casa.total_parlamentares)
            elif _(u"Última alteração de endereco") == atributo:
                lista.append(casa.ult_alt_endereco)
            elif _(u"Nome contato") == atributo:
                if contatos and contatos[0].nome:
                    lista.append(contatos[0].nome.encode("utf-8"))
                else:
                    lista.append('')
            elif _(u"Cargo contato") == atributo:
                if contatos and contatos[0].cargo:
                    lista.append(contatos[0].cargo.encode("utf-8"))
                else:
                    lista.append('')
            elif _(u"Email contato") == atributo:
                if contatos and contatos[0].email:
                    lista.append(contatos[0].email.encode("utf-8"))
                else:
                    lista.append('')
            else:
                pass

        writer.writerow(lista)

    return response

def portfolio(request):
    page = request.GET.get('page', 1)
    regiao = request.GET.get('regiao', None)
    uf_id = request.GET.get('uf', None)
    meso_id = request.GET.get('meso', None)
    micro_id = request.GET.get('micro', None)
    
    data = {}
    data['errors'] = []
    data['messages'] = []
    data['regioes'] = UnidadeFederativa.REGIAO_CHOICES
    casas = None
    gerente_contas = None
    
    if request.method == 'POST':
        form = PortfolioForm(data=request.POST)
        if form.is_valid():
            gerente_contas = form.cleaned_data['gerente_contas']
        else:
            data['errors'].append(_(u"Dados inválidos"))
        
    if micro_id:
        microrregiao = get_object_or_404(Microrregiao, pk=micro_id)
        mesorregiao = microrregiao.mesorregiao 
        uf = mesorregiao.uf
        data['regiao'] = uf.regiao
        data['uf_id'] = uf.pk
        data['meso_id'] = mesorregiao.pk
        data['micro_id'] = microrregiao.pk
        data['ufs'] = UnidadeFederativa.objects.filter(regiao=uf.regiao)
        data['mesorregioes'] = uf.mesorregiao_set.all()
        data['microrregioes'] = mesorregiao.microrregiao_set.all()
        data['form'] = PortfolioForm(_(u'Atribuir casas da microrregiao %s para') % (unicode(microrregiao),))
        data['querystring'] = 'micro=%s' %  (microrregiao.pk,)
        casas = CasaLegislativa.objects.filter(municipio__microrregiao=microrregiao)
    elif meso_id:
        mesorregiao = get_object_or_404(Mesorregiao, pk=meso_id)
        uf = mesorregiao.uf
        data['regiao'] = uf.regiao
        data['uf_id'] = uf.pk
        data['meso_id'] = mesorregiao.pk
        data['ufs'] = UnidadeFederativa.objects.filter(regiao=uf.regiao)
        data['mesorregioes'] = uf.mesorregiao_set.all()
        data['microrregioes'] = mesorregiao.microrregiao_set.all()
        data['form'] = PortfolioForm(_(u'Atribuir casas da mesorregiao %s para') % (unicode(mesorregiao),))
        data['querystring'] = 'meso=%s' %  (mesorregiao.pk,)
        casas = CasaLegislativa.objects.filter(municipio__microrregiao__mesorregiao=mesorregiao)
    elif uf_id:
        uf = get_object_or_404(UnidadeFederativa, pk=uf_id)
        data['regiao'] = uf.regiao
        data['uf_id'] = uf.pk
        data['ufs'] = UnidadeFederativa.objects.filter(regiao=uf.regiao)
        data['mesorregioes'] = uf.mesorregiao_set.all()
        data['form'] = PortfolioForm(_(u'Atribuir casas do estado %s para') % (unicode(uf),))
        data['querystring'] = 'uf=%s' %  (uf.pk,)
        casas = CasaLegislativa.objects.filter(municipio__uf=uf)
    elif regiao:
        data['regiao'] = regiao 
        data['ufs'] = UnidadeFederativa.objects.filter(regiao=regiao)
        data['form'] = PortfolioForm(_(u'Atribuir casas da região %s para') % [x[1] for x in UnidadeFederativa.REGIAO_CHOICES if x[0]==regiao][0])
        data['querystring'] = 'regiao=%s' %  (regiao,)
        casas = CasaLegislativa.objects.filter(municipio__uf__regiao=regiao)
        
    if casas:
        if gerente_contas:
            count = casas.update(gerente_contas=gerente_contas)
            data['messages'].append(ungettext(
                u"%(count)s casa atribuída para %(name)s",
                u"%(count)s casas atribuídas para %(name)s",
                count) % {'count': count, 'name': unicode(gerente_contas)})
        
        casas = casas.order_by('municipio__uf', 'municipio__microrregiao__mesorregiao',
                               'municipio__microrregiao', 'municipio')
        
        casas.prefetch_related('municipio', 'municipio__uf', 'municipio__microrregiao',
                               'municipio__microrregiao__mesorregiao', 'gerente_contas')
        
        paginator = Paginator(casas, 30)
        try:
            pagina = paginator.page(page)
        except (EmptyPage, InvalidPage):
            pagina = paginator.page(paginator.num_pages)
        data['page_obj'] = pagina
        
    return render(request, 'casas/portfolio.html', data)