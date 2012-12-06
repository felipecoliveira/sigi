#-*- coding:utf-8 -*-
import datetime
from sigi.apps.casas.models import CasaLegislativa
from sigi.apps.convenios.models import Convenio, Projeto
from sigi.apps.contatos.models import UnidadeFederativa
from sigi.apps.servicos.models import TipoServico
from sigi.apps.diagnosticos.models import Diagnostico
from sigi.apps.metas.models import Meta

def charts_data(request):
    '''
        Busca informacoes para a criacao dos graficos e resumos
    '''

    projetos = Projeto.objects.all()
    convenios = Convenio.objects.all()
    convenios_assinados = convenios.exclude(data_retorno_assinatura=None)

    tabela_resumo_camara = busca_informacoes_camara()
    tabela_resumo_seit = busca_informacoes_seit()
    tabela_resumo_diagnostico = busca_informacoes_diagnostico()
    g_conv_proj = grafico_convenio_projeto(convenios)
    g_convassinado_proj = grafico_convenio_projeto(convenios_assinados)

    return {        
        'tabela_resumo_camara' : tabela_resumo_camara,
        'tabela_resumo_seit' : tabela_resumo_seit,
        'tabela_resumo_diagnostico': tabela_resumo_diagnostico,
        'g_conv_proj': g_conv_proj,
        "g_convassinado_proj":g_convassinado_proj,
        'metas': Meta.objects.all(),
    }

def busca_informacoes_camara():
    '''
        Busca informacoes no banco para montar tabela de resumo de camaras por projeto
        Retorna um dicionario de listas
    '''    
    camaras = CasaLegislativa.objects.filter(tipo__sigla='CM')
    convenios = Convenio.objects.filter(casa_legislativa__tipo__sigla='CM')
    projetos = Projeto.objects.all()

    convenios_assinados = convenios.exclude(data_retorno_assinatura=None)
    convenios_em_andamento = convenios.filter(data_retorno_assinatura=None)

    convenios_sem_adesao = convenios.filter(data_adesao=None)
    convenios_com_adesao = convenios.exclude(data_adesao=None)

    convenios_com_aceite = convenios.exclude(data_termo_aceite=None)

    camaras_sem_processo = camaras.filter(convenio=None)    

    # Criacao das listas para o resumo de camaras por projeto

    cabecalho_topo = ['',] # Cabecalho superior da tabela

    lista_total = []
    lista_nao_aderidas =  []
    lista_aderidas = []
    lista_convenios_assinados = []
    lista_convenios_em_andamento = []
    lista_camaras_equipadas = []
    for projeto in projetos:
        conv_sem_adesao_proj = convenios_sem_adesao.filter(projeto=projeto)
        conv_com_adesao_proj = convenios_com_adesao.filter(projeto=projeto)
        conv_assinados_proj  = convenios_assinados.filter(projeto=projeto)
        conv_em_andamento_proj = convenios_em_andamento.filter(projeto=projeto)
        conv_equipadas_proj = convenios_com_aceite.filter(projeto=projeto)


        cabecalho_topo.append(projeto.sigla)
        lista_total.append(camaras.filter(convenio__projeto=projeto).count())
        lista_nao_aderidas.append(camaras.filter(convenio__in=conv_sem_adesao_proj).count() )
        lista_aderidas.append(camaras.filter(convenio__in=conv_com_adesao_proj).count())
        lista_convenios_assinados.append(camaras.filter(convenio__in=conv_assinados_proj).count())
        lista_convenios_em_andamento.append(camaras.filter(convenio__in=conv_em_andamento_proj).count())
        lista_camaras_equipadas.append(camaras.filter(convenio__in=conv_equipadas_proj).count())
        
    # Monta linhas de diagnosticos
    lista_diagnosticos_digitados = ['', '', Diagnostico.objects.count()]
    lista_diagnosticos_publicados = ['', '', Diagnostico.objects.filter(publicado=True).count()]

    # Cabecalho da esquerda na tabela
    cabecalho_esquerda = (
        u'Câmaras municipais',
        u'Câmaras municipais não aderidas',
        u'Câmaras municipais aderidas',
        u'Câmaras municipais com convênios assinados',
        u'Câmaras municipais convênios em andamento',
        u'Câmaras municipais equipadas',
        u'Diagnósticos digitados',
        u'Diagnósticos publicados'
    )

    linhas = (
        lista_total,
        lista_nao_aderidas,
        lista_aderidas,
        lista_convenios_assinados,
        lista_convenios_em_andamento,
        lista_camaras_equipadas,
        lista_diagnosticos_digitados,
        lista_diagnosticos_publicados
    )

    # Unindo as duas listass para que o cabecalho da esquerda fique junto com sua
    # respectiva linha
    lista_zip = zip(cabecalho_esquerda,linhas)

    # Retornando listas em forma de dicionario
    return {        
        u'cabecalho_topo': cabecalho_topo,
        u'lista_zip': lista_zip,
        u'total_camaras' : camaras.count(),
        u'camaras_sem_processo': camaras_sem_processo.count(),
    }

def grafico_convenio_projeto(convenios):    
    projetos = Projeto.objects.all()

    lista_convenios = []
    for projeto in projetos:
        lista_convenios.append(convenios.filter(projeto=projeto).count())

    dic = {
        "total_convenios":("Total: " + str(convenios.count())),
        "convenios":lista_convenios,
        "projetos":projetos
    }
    return dic

def busca_informacoes_seit():
    mes_atual = datetime.date.today().replace(day=1)
    mes_anterior = mes_atual - datetime.timedelta(days=1)

    result = [{'nome': '',
               'total': 'Total de casas atendidas',
               'novos_mes_anterior': 'Novas casas em %s/%s' % (mes_anterior.month, mes_anterior.year),
               'novos_mes_atual': 'Novas casas em %s/%s' % (mes_atual.month, mes_atual.year)}]
    
    for tipo_servico in TipoServico.objects.all():
        result.append(
            {'nome': tipo_servico.nome,
             'total': tipo_servico.servico_set.filter(data_desativacao=None).count(),
             'novos_mes_anterior': tipo_servico.servico_set.filter(data_desativacao=None, data_ativacao__year=mes_anterior.year, data_ativacao__month=mes_anterior.month).count(),
             'novos_mes_atual': tipo_servico.servico_set.filter(data_desativacao=None, data_ativacao__year=mes_atual.year, data_ativacao__month=mes_atual.month).count(),
            }
        )

    return result

def busca_informacoes_diagnostico():
    return [
        {'title': 'Diagnósticos digitados', 'count': Diagnostico.objects.count()},
        {'title': 'Diagnósticos publicados', 'count': Diagnostico.objects.filter(publicado=True).count()},
    ]