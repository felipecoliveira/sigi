# -*- coding: utf-8 -*-
#
# sigi.apps.servicos.management.commands.atualiza_uso_servico
#
# Copyright (c) 2012 by Interlegis
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
from django.core.management.base import BaseCommand
from sigi.apps.metas.views import gera_map_data_file

class Command(BaseCommand):
    help = u'Gera arquivo de dados de plotagem do mapa de atuação do Interlegis.'
    def handle(self, *args, **options):
        result = gera_map_data_file(cronjob=True)
        self.stdout.write(result+"\n")