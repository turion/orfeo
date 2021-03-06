#!/usr/bin/python
# -*- coding: utf-8 -*-

#~ import warnings
#~ warnings.simplefilter("error")

import pulp
import sys
import argparse

parser = argparse.ArgumentParser(description="Mache etwas mit einem Stundenplan")
parser.add_argument("xml", help="Der Bezeichner des XML-Datensatzes, von dem die Berechnung durchgeführt wird")
parser.add_argument("-g", "--global", action="store_true", dest="glob", help="Berechnet den globalen Stundenplan (neu)")
parser.add_argument("-gz", "--globalzeit", action="store_true", help="Zeit|Thema|Betreuer|Raum")
parser.add_argument("-gb", "--globalbetreuer", action="store_true", help="Betreuer|Zeit|Thema|Raum|Präferenz")
parser.add_argument("-gt", "--globalthema", action="store_true", help="Thema|Zeiten|Betreuer|Benötigt|Bringt bei|Beliebtheit")
parser.add_argument("-gr", "--globalraum", action="store_true", help="Zeit|Raum")
parser.add_argument("-l", "--lokal", action="store_true", help="Berechnet den lokalen Stundenplan (neu)")
parser.add_argument("-lz", "--lokalzeit", action="store_true", help="Zeit|Thema|Betreuer|Raum|#Teilnehmer")
parser.add_argument("-ls", "--lokalschueler", action="store_true", help="Schüler|Zeit|Thema|Raum|Präferenz")
parser.add_argument("-lt", "--lokalthema", action="store_true", help="Thema|Zeiten|Betreuer|Benötigt|Bringt bei|Beliebtheit|#Teilnehmer")
parser.add_argument("-lg", "--lokalguete", action="store_true", help="Statistiken")
parser.add_argument("-t", "--tex", action="store_true", help="Kursübersicht und Stundenpläne TeXen")
args = parser.parse_args() # Das muss vor der Einbindung von orpheus kommen
sys.argv = [sys.argv[0]] # Weil er sonst im orpheus-Modul das erste Argument für einen Benutzernamen hält

from glob import Global
from lokal import Lokal
#import daten

import inputs.xmlsource as input_backend
problem = input_backend.Problem(args.xml)
problem.printinfos()
if args.glob:
	glob = Global.calculate(problem)
	glob.save()
else:
	glob = Global.load(problem)
if args.globalzeit:
	glob.zeige_zeit()
if args.globalbetreuer:
	glob.zeige_betreuer()
if args.globalthema:
	glob.zeige_thema()
if args.globalraum:
	glob.zeige_raum()
lokal = None
if args.lokal:
	lokal = Lokal.calculate(problem, glob)
	lokal.save()
else:
	lokal = Lokal.load(problem, glob)
if args.lokalzeit:
	lokal.zeige_zeit()
if args.lokalschueler:
	lokal.zeige_schueler()
if args.lokalthema:
	lokal.zeige_thema()
if args.lokalguete:
	lokal.zeige_guete()
if args.tex:
	lokal.mache_kursplan_tex()
	lokal.mache_stundenplaene_tex()
