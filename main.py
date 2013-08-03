#!/usr/bin/python2
# -*- coding: utf-8 -*-

#~ import warnings
#~ warnings.simplefilter("error")

import pulp
import sys
import argparse

parser = argparse.ArgumentParser(description="Mache etwas mit einem Stundenplan")
parser.add_argument("-x", "--xml", action="store_true", help="Wählt eine XML-Datei als Eingabe, und nicht die Datenbank")
parser.add_argument("-g", "--global", action="store_true", dest="glob", help="Berechnet den globalen Stundenplan (neu)")
parser.add_argument("-gz", "--globalzeit", action="store_true", help="Zeit|Thema|Betreuer|Raum")
parser.add_argument("-gb", "--globalbetreuer", action="store_true", help="Betreuer|Zeit|Thema|Raum|Präferenz")
parser.add_argument("-gt", "--globalthema", action="store_true", help="Thema|Zeiten|Betreuer|Benötigt|Bringt bei|Beliebtheit")
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

if args.xml:
	import inputs.xml as input_backend
	quit("Zur Zeit noch nicht unterstützt")
else:
	import inputs.daten as input_backend
problem = input_backend.Problem()
problem.printinfos()
glob = None
if args.glob:
	glob = Global.calculate(problem)
	glob.save("global.txt")
else:
	glob = Global.load(problem,"global.txt")
if args.globalzeit:
	glob.zeige_zeit()
if args.globalbetreuer:
	glob.zeige_betreuer()
if args.globalthema:
	glob.zeige_thema()
lokal = None
if args.lokal or args.glob:
	lokal = Lokal.calculate(problem, glob)
	lokal.save("lokal.txt")
else:
	lokal = Lokal.load(problem,glob,"lokal.txt")
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
