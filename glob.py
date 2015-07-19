#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pulp
from prettytable import PrettyTable # Das ist ein Pythonpaket
from inputs import Bessere, PulpMatrix, lpsolver

# Speichert eine Lösung des globalen Stundenplanproblems (wann hält welcher Betreuer welches Thema wo?)
class Global(object):
	def __init__(self, problem):
		self.problem = problem
	
	def _calculate(self):
		p = self.problem
		print([(z.titel, z.name, z.stelle) for z in p.zeiteinheiten])
		prob = pulp.LpProblem("Stundenplan", pulp.LpMaximize)
		
		raum_belegungen = PulpMatrix("raum_belegungen", (p.raeume, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		
		# Raum nur benutzen, wenn er verfügbar ist (insbesondere zu jedem Zeitpunkt nur höchstens einmal)
		for r in p.raeume:
			for z in p.zeiteinheiten:
				prob += pulp.lpSum([raum_belegungen[r,t,z] for t in p.themen]) <= p.raumverfuegbar[r,z]
		
		# Dadurch wird automatisch pro (Thema, Zeit) nur ein Raum belegt
		thema_findet_dann_statt = PulpMatrix("thema_findet_dann_statt", (p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for t, z in p.muss_stattfinden_an:
			#print("{} muss stattfinden an {}".format(t.titel, z.name))
			prob += thema_findet_dann_statt[t,z] == 1

		fortsetzung_findet_dann_statt = PulpMatrix("fortsetzung_findet_dann_statt", (p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for t in p.themen:
			for z in p.zeiteinheiten:
				prob += thema_findet_dann_statt[t,z] == pulp.lpSum([raum_belegungen[r,t,z] for r in p.raeume])
				prob += fortsetzung_findet_dann_statt[t,z] <= thema_findet_dann_statt[t,z]
		#TODO Der richtige Ort, um softzucoden, welches Thema wann stattfindet
		# Zweistündige Themen
			if t.laenge not in (1,2):
				raise ValueError("Thema {} hat verbotene Länge {}".format(t.titel, t.laenge))
			if t.laenge == 2:
				#print("Zweieinheitiges Thema {}".format(t.titel))
				for z, fortsetzung_z in zip(p.zeiteinheiten[:-1], p.zeiteinheiten[1:]):
					if (fortsetzung_z.timestamp - z.timestamp) < 0:
						raise ValueError("Zeiteinheiten falsch sortiert")
					prob += fortsetzung_findet_dann_statt[t,fortsetzung_z] <= thema_findet_dann_statt[t,z]
					prob += thema_findet_dann_statt[t,z] + thema_findet_dann_statt[t,fortsetzung_z] -fortsetzung_findet_dann_statt[t,fortsetzung_z] - fortsetzung_findet_dann_statt[t,z] <= 1
					prob += fortsetzung_findet_dann_statt[t, fortsetzung_z] == thema_findet_dann_statt[t,z] - fortsetzung_findet_dann_statt[t,z]
					if (fortsetzung_z.timestamp - z.timestamp) < 60*60*3: # Direkt nebeneinanderliegende Zeiteinheiten (ohne große Pause dazwischen)
						prob += fortsetzung_findet_dann_statt[t,fortsetzung_z] + fortsetzung_findet_dann_statt[t,z] <= 1
						#for raum in p.raeume: # Nicht in irgendeinem Raum, sondern im selben #FIXME Bug: Das sollte nur dann gefordert werden, wenn denn auch eine Fortsetzung stattfindet. 
							#prob += raum_belegungen[r,t,fortsetzung_z] == raum_belegungen[r,t,z]
					else: # Nicht zerteilen
						prob += fortsetzung_findet_dann_statt[t,fortsetzung_z] == 0
				letzte_zeiteinheit = p.zeiteinheiten[-1]
				prob += thema_findet_dann_statt[t,letzte_zeiteinheit] - fortsetzung_findet_dann_statt[t,letzte_zeiteinheit] == 0 # Wenn es am Ende noch mal stattfindet, dann nur als Fortsetzung
			else:
				for z in p.zeiteinheiten:
					prob += fortsetzung_findet_dann_statt[t,z] == 0
		
		# Dafür sorgen, dass es genug Kurse für alle gibt
		for z in p.zeiteinheiten:
			prob += pulp.lpSum([raum_belegungen[r,t,z]*r.max_personen for t in p.themen for r in p.raeume]) >= sum([p.istda[s,z] for s in p.schueler])
			prob += pulp.lpSum([thema_findet_dann_statt[t,z] for t in p.themen]) >= 4
		
		# Spezialräume
		nurinraeumen = Bessere((p.themen,), [])
		for r in p.raeume:
			if r.themen_id is not None: # Der Raum ist für ein spezielles Thema vorgesehen
				nurinraeumen[r.themen_id] += [r]
				for t in p.themen:
					if t.id != r.themen_id: # Also werden alle anderen Themen dort nicht stattfinden
						for z in p.zeiteinheiten:
							prob += raum_belegungen[r,t,z] == 0
		# Richtige Sachen in Spezialräumen stattfinden lassen
		for t in p.themen:
			if len(nurinraeumen[t]):
				for r in p.raeume:
					if not r in nurinraeumen[t]:
						for z in p.zeiteinheiten:
							prob += raum_belegungen[r,t,z] == 0
		
		# Themen, die einen Beamer brauchen, nur in beamerbehafteten Räumen stattfinden lassen
		for t in p.themen:
			if t.beamer:
				for r in p.raeume:
					if not r.beamer:
						for z in p.zeiteinheiten:
							prob += raum_belegungen[r,t,z] == 0
		
		
		print("Betreuer")
		betreuer_belegungen = PulpMatrix("betreuer_belegungen", (p.betreuer, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for z in p.zeiteinheiten:
			for b in p.betreuer:
				# Jeder Betreuer kann pro Zeit nur ein Thema betreuen und auch das nur, wenn er da ist
				prob += pulp.lpSum([betreuer_belegungen[b,t,z] for t in p.themen]) <= p.istda[b,z]
				# Gastbetreuer wollen immer was zu tun haben # Nein, eigentlich nicht, kann zu Bugs führen wenn deren Experiment z.B. nicht immer verfügbar ist
				#if b.gastbetreuer:
					#prob += pulp.lpSum([betreuer_belegungen[b,t,z] for t in p.themen]) == p.istda[b,z]
			for t in p.themen:
				# Thema findet nur statt, wenn ein Betreuer das macht
				prob += thema_findet_dann_statt[t,z] == pulp.lpSum([betreuer_belegungen[b,t,z] for b in p.betreuer])
		# Speichert, welcher Betreuer irgendwann mal welches Thema hält
		betreuer_themen = PulpMatrix("betreuer_themen", (p.betreuer, p.themen), 0, 1, pulp.LpInteger)
		for b in p.betreuer:
			for t in p.themen:
				for z in p.zeiteinheiten:
					# Ein Betreuer kann ein Thema nur belegen, wenn es ihm zugeordnet ist
					prob += betreuer_themen[b,t] >= betreuer_belegungen[b,t,z]
				# Jeder Betreuer sollte seine Themen mindestens einmal halten
				prob += betreuer_themen[b,t] <= pulp.lpSum([betreuer_belegungen[b,t,z] for z in p.zeiteinheiten])
		
		# Jedes Thema wird von genau einem Betreuer gehalten (insbesondere wird jedes Thema mindestens einmal gehalten)
		# TODO Vielleicht <= statt == nehmen?
		# TODO Was ist, wenn mehrere Betreuer sich ein Thema teilen wollen?
		for t in p.themen:
			prob += pulp.lpSum([betreuer_themen[b,t] for b in p.betreuer]) == 1
		
		# Betreuer-Präferenzen
		for b in p.betreuer:
			for t in p.themen:
				if p.pref[b,t] == 3: # Unbedingt und sonst niemand
					# Das bedeutet, dass jedes Thema, das jemand unbedingt machen will, irgendwann angeboten wird (TODO so OK?)
					prob += betreuer_themen[b,t] == 1
					for ab in p.betreuer:
						if ab.id != b.id:
							prob += betreuer_themen[ab,t] == 0
				elif p.pref[b,t] == -1: # Auf keinen Fall
					prob += betreuer_themen[b,t] == 0
		
		
		thema_findet_so_oft_statt = PulpMatrix("thema_findet_so_oft_statt", (p.themen,), 0, None, pulp.LpInteger)
		for t in p.themen:
			prob += thema_findet_so_oft_statt[t] == pulp.lpSum([thema_findet_dann_statt[t,z] for z in p.zeiteinheiten]) - pulp.lpSum([fortsetzung_findet_dann_statt[t,z] for z in p.zeiteinheiten])
		
		# Zu jedem Zeitpunkt sollten >= 2 Betreuer frei haben
		for z in p.zeiteinheiten:
			prob += pulp.lpSum(p.istda[b,z]-sum(betreuer_belegungen[b,t,z] for t in p.themen) for b in p.betreuer) >= 2
		# Zu jedem Zeitpunkt sollte 1 Organisator verfügbar sein.
		for z in p.zeiteinheiten:
			prob += pulp.lpSum(p.istda[b,z]-sum(betreuer_belegungen[b,t,z] for t in p.themen) for b in p.organisatoren) >= 1
		# Jeder Organisator sollte von 4 Stunden 1 Freistunde haben
		for b in p.organisatoren:
			#print("Stelle frei {}".format(b.name))
			prob += pulp.lpSum(p.istda[b,z]-sum(betreuer_belegungen[b,t,z] for t in p.themen) for z in p.zeiteinheiten)*4 >= sum(p.istda[b,z] for z in p.zeiteinheiten) - 3
		
		#korrelationen_einbeziehen = False
		#if korrelationen_einbeziehen:
			#da_muss_einiges_umgeschrieben_werden_weil_thema_findet_dann_statt_jetzt_eine_bessere_matrix_ist
			#print("Korrelationen")
			#l = len(p.themen)
			#p.themen_wunschkorrelation2 = [[0]*l for i in range(l)]
			#for anmeldung, person in p.schueler:
				#wuensche = orpheus.daten.wunschp.themen.filter_by(personen_id=person.id, jahr=jahr).filter(Wunschp.themen.gerne>0).all()
				#for wunsch1 in wuensche:
					#thema1index = p.themen.index(wunsch1.p.themen)
					#for wunsch2 in wuensche:
						#thema2index = p.themen.index(wunsch2.p.themen)
						#if thema2index > thema1index:
							#p.themen_wunschkorrelation2[thema1index][thema2index] = int(wunsch1.gerne * wunsch2.gerne)
			#p.themen_korrelation2 = PulpMatrix("p.themen_korrelation2", (p.themen, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
			##Redundante Einträge der symmetrischen Matrix eliminieren
			#for thema1 in p.themen:
				#for thema2 in p.themen:
					#p.themenindex1 = p.themen.index(thema1)
					#p.themenindex2 = p.themen.index(thema2)
					#indexdifferenz = p.themenindex2 - p.themenindex1
					#for zeiteinheit in p.zeiteinheiten:
						#p.zeiteinheitenindex = p.zeiteinheiten.index(zeiteinheit)
						#if indexdifferenz < 0:
							#prob += p.themen_korrelation2[thema1,thema2,zeiteinheit] == p.themen_korrelation2[thema2,thema1,zeiteinheit] # Symmetrie
						#elif indexdifferenz == 0:
							#prob += p.themen_korrelation2[thema1,thema2,zeiteinheit] == 0
						#elif indexdifferenz > 0: # nur in diesem Fall wird p.themen_korrelation2 überhaupt sinnvoll definiert und verwandt
							#anzahl_stattfindende = thema_findet_dann_statt[p.themenindex1][p.zeiteinheitenindex] + thema_findet_dann_statt[p.themenindex2][p.zeiteinheitenindex]
							#prob += p.themen_korrelation2[thema1,thema2,zeiteinheit] >= anzahl_stattfindende - 1
							##prob += p.themen_korrelation2[thema1,thema2,zeiteinheit] * 4 <= anzahl_stattfindende + 1 # TODO: Müsste eigentlich auch mit gehen
							## Erklärung dieser beiden lustigen Zwangsbedingungen: Fallunterscheidung:
							## Keins der Themen findet statt: -1 <= korrelation <= 1/4, also korrelation == 0
							## Eins findet statt: 0 <= korrelation <= 3/4, also korrelation == 0
							## Beide finden statt: 1 <= korrelation <= 5/4, also korrelation == 1
			##TODO: Mit Korrelationen was anstellen
			##TODO: Korrelationen von Einführungsvorträgen (?)
			
		
		print("Optimierung")
		
		#FIXME: Bei Bedarf hier noch Schranken auf thema_findet_so_oft_statt
		for thema in p.themen:
			prob += thema_findet_so_oft_statt[thema] <= 4
			prob += thema_findet_so_oft_statt[thema] >= 1
			if p.thema_beliebtheit[thema] > 26: #TODO vielleicht lieber die 15 beliebtesten Themen oder so
				prob += thema_findet_so_oft_statt[thema] >= 2

		# Immer genug akzeptierte Themen für alle Schüler, außer für sehr wählerische
		for s in p.schueler:
			akzeptierte_themen = [t for t in p.themen if p.pref[s,t] >= 0]
			if len(akzeptierte_themen) < 25: #FIXME
				#print("Wählerisch: {}".format(s.name))
				pass
			else:
				for z in p.zeiteinheiten:#FIXME
					prob += pulp.lpSum([thema_findet_dann_statt[t,z] for t in akzeptierte_themen]) >= 1


		tatsaechlicher_platz = PulpMatrix("tatsaechlicher_platz", (p.themen, p.zeiteinheiten), 0, None, pulp.LpContinuous)
		platz = PulpMatrix("platz", (p.themen, p.zeiteinheiten), 0, None, pulp.LpContinuous)
		geschaetzte_kompetenzen = PulpMatrix("geschaetzte_kompetenzen", (p.themen,), 0, None, pulp.LpContinuous)
		for t in p.themen:
			prob += geschaetzte_kompetenzen == len([schuel for schuel in p.schueler if p.pref[schuel,t] == -1])*0.3 # Präferenz -1 bedeutet "interessiert mich nicht oder kenne ich schon"

		#TODO Hier werden mehrstündige Themen noch nicht richtig betrachtet
		for t in p.themen:
			for z in p.zeiteinheiten:
				prob += platz[t,z] <= thema_findet_dann_statt[t,z]*t.gutegroesse() # Fabians FIXME
				prob += tatsaechlicher_platz[t,z] == pulp.lpSum([raum_belegungen[r,t,z] * r.max_personen for r in p.raeume])
				#prob += platz[t,z] <= pulp.lpSum([raum_belegungen[r,t,z] * r.max_personen for r in p.raeume]) *1.1 + 3
				#prob += platz[t,z] >= pulp.lpSum([raum_belegungen[r,t,z] * r.max_personen for r in p.raeume]) *0.9 - 3
				#prob += platz[t,z] >= pulp.lpSum([raum_belegungen[r,t,z] * r.max_personen for r in p.raeume]) * 0.5
				for v in p.thema_voraussetzungen[t]:
					prob += platz[t,z] <= pulp.lpSum([platz[v,z1] for z1 in p.zeiteinheiten if z1.stelle < z.stelle]) * 3 #FIXME test geschaetzte_kompetenzen
		#Fabian Gundlach: platz[t,z] sollte eigentlich eine Approximation an die Anzahl Leute sein, die Thema t zum Zeitpunkt z sinnvoll anhцren kцnnen. Da muss genug Platz im Kurs sein (Zeile 187) und genug Leute mьssen die Voraussetzungen kennen (Zeile 190).
		#Fabian Gundlach: Haben die Themen mit platz=0 alle viele Voraussetzungen (inkl. den indirekten)?
		#Manuel: ach so, man müsste ja eigentlich so machen, dass man vom angeforderten Platz die Anzahl der schon kompetenten Schüler abzieht, denn die brauchen ja nicht die Voraussetzung		
		#Bzw zu platz die Anzahl der kompetenten dazuzählt
		
		# Voraussetzung muss mindestens einmal vor dem voraussetzenden Thema kommen #TODO Das ist zu stark
		#for t in p.themen:
			#for v in p.thema_voraussetzungen[t]:
				#for i, z in enumerate(p.zeiteinheiten):
					#prob += pulp.lpSum(thema_findet_dann_statt[v,davor] for davor in p.zeiteinheiten[:i]) >= thema_findet_dann_statt[t,z]
		
		ueberfuellung = PulpMatrix("ueberfuellung", (p.themen,), 0, None, pulp.LpContinuous)
		for t in p.themen:
			prob += ueberfuellung[t] >= p.thema_beliebtheit[t] - pulp.lpSum([platz[t,z] for z in p.zeiteinheiten])
		tatsaechliche_ueberfuellung = PulpMatrix("tatsaechliche_ueberfuellung", (p.themen,), 0, None, pulp.LpContinuous)
		for t in p.themen:
			prob += tatsaechliche_ueberfuellung[t] >= p.thema_beliebtheit[t] - pulp.lpSum([tatsaechlicher_platz[t,z] for z in p.zeiteinheiten])
			for z in p.zeiteinheiten:
				for v in p.thema_voraussetzungen[t]:
					prob += tatsaechlicher_platz[t,z] <= pulp.lpSum([tatsaechlicher_platz[v,z1] for z1 in p.zeiteinheiten if z1.stelle < z.stelle]) + geschaetzte_kompetenzen[t]
		
		#unterfuellung = PulpMatrix("unterfuellung", (p.themen,), 0, None, pulp.LpContinuous)
		#for t in p.themen:
			#prob += unterfuellung[t] >= -p.thema_beliebtheit[t] + pulp.lpSum([thema_findet_dann_statt[t,z]*t.gutegroesse() for z in p.zeiteinheiten])
		
		#beliebtheit = pulp.lpSum([-ueberfuellung[t] - 0.1*unterfuellung[t] for t in p.themen])
		beliebtheit = pulp.lpSum([-ueberfuellung[t] for t in p.themen])
		tatsaechliche_beliebtheit = pulp.lpSum([-tatsaechliche_ueberfuellung[t] for t in p.themen])
		angebot_an_beliebten_themen = pulp.lpSum([tatsaechlicher_platz[t,z] * p.thema_beliebtheit[t] for t in p.themen for z in p.zeiteinheiten])
		
		# vielleicht noch so, dass die erste Voraussetzung vor dem letzten voraussetzenden kommt
		def mittelbare_voraussetzungen(thema, tiefe=3):
			for voraussetzung in p.thema_voraussetzungen[thema]:
				yield voraussetzung
				#yield from unmittelbare_voraussetzungen(voraussetzung) #Mann, wann wird das endlich Py3.3?
				if tiefe > 1:
					for mittelbare_voraussetzung in mittelbare_voraussetzungen(voraussetzung, tiefe-1):
						yield mittelbare_voraussetzung

		so_oft_kommt_es_noch = PulpMatrix("so_oft_kommt_es_noch", (p.themen,p.zeiteinheiten), 0, None, pulp.LpInteger)
		so_oft_war_es_schon = PulpMatrix("so_oft_war_es_schon", (p.themen,p.zeiteinheiten), 0, None, pulp.LpInteger)
		for t in p.themen:
			#print("Denke über {} nach".format(t.titel))
			#for v in mittelbare_voraussetzungen(t):
				#print("Setze Bed. für {} -> {}".format(t.titel, v.titel))
			#input()
			for i, z in enumerate(p.zeiteinheiten):
				prob += so_oft_kommt_es_noch[t,z] == pulp.lpSum([thema_findet_dann_statt[t,spaeter] for spaeter in p.zeiteinheiten[i+1:]])
				prob += so_oft_war_es_schon[t,z] == pulp.lpSum([thema_findet_dann_statt[t,frueher] for frueher in p.zeiteinheiten[:i]])
				for v in mittelbare_voraussetzungen(t):
					prob += so_oft_kommt_es_noch[t,z] + so_oft_war_es_schon[v,z] >= 1
		
		#korrelationsmalus = 0
		#if korrelationen_einbeziehen:
			#print("Korrelationsoptimierung")
			##Themen, die häufig zusammen gewählt werden, sollten nicht oft gemeinsam stattfinden
			##TODO: Alternativen: thema1 häufigkeit + thema2 häufigkeit - korrelation
			#for thema1 in p.themen:
				#p.themenindex1 = p.themen.index(thema1)
				#for thema2 in p.themen:
					#p.themenindex2 = p.themen.index(thema2)
					#korrelationsmalus += pulp.lpSum([p.themen_korrelation2[thema1,thema2,zeiteinheit] for zeiteinheit in p.zeiteinheiten]) * p.themen_wunschkorrelation2[p.themenindex1][p.themenindex2]
		
		gesamtangebot = pulp.lpSum([thema_findet_dann_statt[t,z] for t in p.themen for z in p.zeiteinheiten]) - pulp.lpSum([fortsetzung_findet_dann_statt[t,z] for t in p.themen for z in p.zeiteinheiten])
		
		#reihenfolge = []
		#for zuerst, danach in p.voraussetzungen:
			#for i, z1 in enumerate(p.zeiteinheiten):
				#for z2 in p.zeiteinheiten[i:]:
					#var = pulp.LpVariable("reihenfolge_helfer_{}_{}_{}_{}".format(zuerst.id, danach.id, z1.id, z2.id), 0, 1, pulp.LpInteger)
					#prob += var <= thema_findet_dann_statt[zuerst,z1]
					#prob += var <= thema_findet_dann_statt[danach,z2]
					#reihenfolge.append(var)
		#reihenfolge = pulp.lpSum(reihenfolge) #TODO Was sollte das jetzt nochmal?
		
		print("Statistische Optimierung")
		
		#Mit dieser Wahrscheinlichkeit wird ein Schüler diesen Kurs belegen
		statistische_belegungen = PulpMatrix("statistische_belegungen", (p.schueler, p.themen, p.zeiteinheiten), 0, 1, pulp.LpContinuous)
		for s in p.schueler:
			for zeit in p.zeiteinheiten:
				for thema in p.themen:
					prob += statistische_belegungen[s,thema,zeit] - p.istda[s,zeit] <= thema_findet_dann_statt[thema,zeit]
				prob += pulp.lpSum([statistische_belegungen[s,thema,zeit] for thema in p.themen]) <= 1
		
		statistischer_physikspass = pulp.lpSum([statistische_belegungen[s,thema,zeit] * p.prefbetter[s,thema] for s in p.schueler for t in p.themen for zeit in p.zeiteinheiten])
		
		
		
		print("Dummybelegung")
		
		#Soll sicherstellen, dass es immer eine Belegung gibt, in der kein Schüler etwas machen muss, was er nicht will
		dummy_belegungen = PulpMatrix("dummy_belegungen", (p.schueler, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for s in p.schueler:
			for zeit in p.zeiteinheiten:
				for thema in p.themen:
					prob += dummy_belegungen[s,thema,zeit] - p.istda[s,zeit] <= thema_findet_dann_statt[thema,zeit]
					if p.pref[s,thema] in (-1,0):
						prob += dummy_belegungen[s,thema,zeit] == 0
				prob += pulp.lpSum([dummy_belegungen[s,thema,zeit] for thema in p.themen]) <= 1
		dummyspass = pulp.lpSum([dummy_belegungen[s,thema,zeit] * p.prefbetter[s,thema] for s in p.schueler for t in p.themen for zeit in p.zeiteinheiten])
		#TODO Füge noch weitere Zwangsbedingungen von wegen Raumgrößen etc. hinzu
		
		
		# Die gewichtete Optimierungsfunktion:
		prob += 2*angebot_an_beliebten_themen + beliebtheit + tatsaechliche_beliebtheit + gesamtangebot + dummyspass #+ 0.01*reihenfolge #+ (-0.5)*korrelationsmalus
		#prob += statistischer_physikspass
		# Gerechtigkeitsdummys
		# Dummybedingungen um Fehler zu finden. Außerdem ist das eigentlich relativ gerecht.
		# Jeder Betreuer, sofern er kein Organisator ist, sollte mindestens 7 Mal etwas tun
		for b in p.betreuer:
			if b not in p.organisatoren:
				prob += pulp.lpSum([betreuer_belegungen[b,t,z] for t in p.themen for z in p.zeiteinheiten]) >= min(7,sum(p.istda[b,z] for z in p.zeiteinheiten))
		# Jeder Betreuer sollte mindestens 2 verschiedene Themen haben
		# TODO Wieder einfügen, sobald möglich
		#for b in p.betreuer:
			#prob += pulp.lpSum([betreuer_themen[b,t] for t in p.themen]) >= 2
		
		#prob.writeLP("global.lp")
		#prob.writeMPS("global.mps")
		if prob.solve(lpsolver()) != 1:
			raise BaseException("Konnte das Optimierungsproblem nicht lösen")
		
		self.raum_belegungen = raum_belegungen.werte()
		self.betreuer_themen = betreuer_themen.werte()
		self.betreuer_belegungen = betreuer_belegungen.werte()
		self.fortsetzungen = fortsetzung_findet_dann_statt.werte()
		self.so_oft_noch = so_oft_kommt_es_noch.werte()
		self.so_oft_schon = so_oft_war_es_schon.werte()
		self.thema_findet_dann_statt = thema_findet_dann_statt.werte()
		self.thema_findet_so_oft_statt = thema_findet_so_oft_statt.werte()
		#for thema in p.themen:
			#print("{} = {} - {} | {}".format(self.thema_findet_so_oft_statt[thema], sum([self.thema_findet_dann_statt[thema,z] for z in p.zeiteinheiten]), sum([self.fortsetzungen[thema,z] for z in p.zeiteinheiten]), thema.titel))
			#if thema.id in (304,305,306): #Mikhail
				#print(thema.titel)
				#print("so oft noch: ", [int(self.so_oft_noch[thema,zeiteinheit]) for zeiteinheit in p.zeiteinheiten])
				#print("so oft schon:", [int(self.so_oft_schon[thema,zeiteinheit]) for zeiteinheit in p.zeiteinheiten])
				#print("findet statt:", [int(self.thema_findet_dann_statt[thema,zeiteinheit]) for zeiteinheit in p.zeiteinheiten])
			#if thema.laenge == 2:
				#print(thema.titel)
				#print([self.fortsetzungen[thema, zeiteinheit] for zeiteinheit in p.zeiteinheiten])
		#for zeiteinheit in p.zeiteinheiten:
			#for thema in p.themen:
				#if thema_findet_dann_statt[thema, zeiteinheit] == 1:
					#if platz.werte()[thema, zeiteinheit] == 0:
						#print("Kein Platz![?}", thema.titel, zeiteinheit.name)
					#else:
						#print("Platz", thema.titel, zeiteinheit.name)
		self.calcrest()
	
	def calcrest(self):
		p = self.problem
		self.betreuer_stundenplan = Bessere((p.betreuer,p.zeiteinheiten), None)
		self.betreuer_von = Bessere((p.themen,p.zeiteinheiten), None)
		self.betreuer_raumplan = Bessere((p.betreuer,p.zeiteinheiten), None)
		self.raum_von = Bessere((p.themen,p.zeiteinheiten), None)
		for b in p.betreuer:
			for z in p.zeiteinheiten:
				for t in p.themen:
					if self.betreuer_belegungen[b,t,z]:
						self.betreuer_stundenplan[b,z] = t
						self.betreuer_von[t,z] = b
						for r in p.raeume:
							if self.raum_belegungen[r,t,z]:
								self.betreuer_raumplan[b,z] = r
								self.raum_von[t,z] = r
	
	@classmethod
	def calculate(cls, problem):
		x = cls(problem)
		x._calculate()
		return x
	
	def _load(self, filename):
		p = self.problem
		self.raum_belegungen = Bessere((p.raeume,p.themen,p.zeiteinheiten), 0)
		self.betreuer_themen = Bessere((p.betreuer,p.themen), 0)
		self.betreuer_belegungen = Bessere((p.betreuer,p.themen,p.zeiteinheiten), 0)
		gefundene_betreuer = set()
		with open(filename) as f:
			while True:
				line = f.readline()
				if line == "":
					break
				line = line.replace("\n","")
				if line == "" or line[0] == "#":
					continue
				if line[0:2] != "= ":
					raise ValueError("Betreuer erwartet")
				line = line[2:]
				b = None
				for bs in p.betreuer:
					if bs.cname() == line:
						b = bs
				if b is None:
					raise ValueError("Betreuer \"{}\" existiert nicht".format(line))
				if b.id in gefundene_betreuer:
					raise ValueError("Betreuer \"{}\" schon angegeben".format(line))
				gefundene_betreuer.add(b.id)
				for z in p.zeiteinheiten:
					line = f.readline()
					if line == "":
						raise ValueError("Was macht Betreuer \"{}\" zur Zeit \"{}\"?".format(b.cname(),z.name))
					line = line.replace("\n","")
					line = line.split(" <-> ")
					if len(line) != 3:
						raise ValueError("Falsches Format für Betreuer \"{}\" zur Zeit \"{}\"".format(b.cname(),z.name))
					if line[0] != z.name:
						raise ValueError("Falsche Zeit \"{}\" für Betreuer \"{}\" (wollte \"{}\")".format(line[0],b.cname(),z.name))
					if line[1] == "" and line[2] == "":
						continue
					t = None
					for ts in p.themen:
						if ts.titel == line[1]:
							t = ts
					if t is None:
						raise ValueError("Thema \"{}\" existiert nicht (für Betreuer \"{}\" zu Zeit \"{}\")".format(line[1],b.cname(),z.name))
					r = None
					for rs in p.raeume:
						if "{} ({})".format(rs.name,rs.id) == line[2]:
							r = rs
					if r is None:
						raise ValueError("Raum \"{}\" existiert nicht (für Betreuer \"{}\" zu Zeit \"{}\")".format(line[2],b.cname(),z.name))
					self.raum_belegungen[r,t,z] = 1
					self.betreuer_themen[b,t] = 1
					self.betreuer_belegungen[b,t,z] = 1
		if len(gefundene_betreuer) < len(p.betreuer):
			raise ValueError("Nicht alle Betreuer angegeben")
		# Raum nur benutzen, wenn er verfügbar ist (insbesondere zu jedem Zeitpunkt nur höchstens einmal)
		for r in p.raeume:
			for z in p.zeiteinheiten:
				if sum([self.raum_belegungen[r,t,z] for t in p.themen]) > p.raumverfuegbar[r,z]:
					raise ValueError("Raum {} wird zu Zeit {} mehrfach belegt".format(r.name,z.name))
		thema_findet_dann_statt = Bessere((p.themen, p.zeiteinheiten), 0)
		for t in p.themen:
			for z in p.zeiteinheiten:
				thema_findet_dann_statt[t,z] = sum([self.raum_belegungen[r,t,z] for r in p.raeume])
				if thema_findet_dann_statt[t,z] > 1:
					raise ValueError("Thema {} findet zur Zeit {} mehrmals statt".format(t.titel,z.name))
		# Dafür sorgen, dass es genug Kurse für alle gibt
		for z in p.zeiteinheiten:
			if sum([self.raum_belegungen[r,t,z]*r.max_personen for t in p.themen for r in p.raeume]) < sum([p.istda[s,z] for s in p.schueler]):
				raise ValueError("Zu wenig Angebote zur Zeit {}".format(z.name))
		# Spezialräume
		nurinraeumen = Bessere((p.themen,), [])
		for r in p.raeume:
			if r.themen_id: # Der Raum ist für ein spezielles Thema vorgesehen
				nurinraeumen[r.themen_id] += [r]
				for t in p.themen:
					if t.id != r.themen_id: # Also werden alle anderen Themen dort nicht stattfinden
						for z in p.zeiteinheiten:
							if self.raum_belegungen[r,t,z] > 0:
								raise ValueError("Im Spezialraum {} findet falsches Thema {} zur Zeit {} statt".format(r.name,t.titel,z.name))
		# Richtige Sachen in Spezialräumen stattfinden lassen
		for t in p.themen:
			if len(nurinraeumen[t]):
				for r in p.raeume:
					if not r in nurinraeumen[t]:
						for z in p.zeiteinheiten:
							if self.raum_belegungen[r,t,z] > 0:
								raise ValueError("Thema {} findet zur Zeit {} nicht in seinem Spezialraum statt".format(t.titel,z.name))
		for z in p.zeiteinheiten:
			for b in p.betreuer:
				# Jeder Betreuer kann pro Zeit nur ein Thema betreuen und auch das nur, wenn er da ist
				if sum([self.betreuer_belegungen[b,t,z] for t in p.themen]) > p.istda[b,z]:
					raise ValueError("Betreuer {} soll zur Zeit {} etwas tun, obwohl er nicht da ist".format(b.cname(),z.name))
		# Jedes Thema wird von genau einem Betreuer gehalten (insbesondere wird jedes Thema mindestens einmal gehalten)
		# TODO Vielleicht <= statt == nehmen?
		# TODO Was ist, wenn mehrere Betreuer sich ein Thema teilen wollen?
		for t in p.themen:
			if sum([self.betreuer_themen[b,t] for b in p.betreuer]) != 1:
				raise ValueError("Thema {} wird nicht von genau einem Betreuer gehalten".format(t.titel))
		# Betreuer-Präferenzen
		for b in p.betreuer:
			for t in p.themen:
				if p.pref[b,t] == 3: # Unbedingt und sonst niemand
					# Das bedeutet, dass jedes Thema, das jemand unbedingt machen will, irgendwann angeboten wird (TODO so OK?)
					if self.betreuer_themen[b,t] != 1:
						raise ValueError("Betreuer {} bekommt Thema {} nicht, obwohl er es unbedingt will".format(b.cname(),t.titel))
					for ab in p.betreuer:
						if ab.id != b.id:
							if self.betreuer_themen[ab,t] != 0:
								raise ValueError("Betreuer {} bekommt Thema {}, obwohl {} das unbedingt will".format(ab.cname(),t.titel,b.cname()))
				elif p.pref[b,t] == -1: # Auf keinen Fall
					if self.betreuer_themen[b,t] != 0:
						raise ValueError("Betreuer {} bekommt Thema {}, obwohl er das auf keinen Fall will".format(b.cname(),t.titel))
		self.calcrest()
	
	@classmethod
	def load(cls, problem):
		x = cls(problem)	
		x._load("results/{}/Global.txt".format(problem.problem_id))
		return x
	
	def save(self):
		p = self.problem
		os.makedirs("results/{}".format(p.problem_id), exist_ok=True)
		with open("results/{}/Global.txt".format(p.problem_id), "w") as f:
			f.write("# Du darfst diese Datei editieren um den Stundenplan zu ändern\n")
			for b in p.betreuer:
				f.write("= {}\n".format(b.cname()))
				for z in p.zeiteinheiten:
					t = self.betreuer_stundenplan[b,z]
					tn = t.titel if t is not None else ""
					r = self.betreuer_raumplan[b,z]
					rn = "{} ({})".format(r.name,r.id) if r is not None else ""
					f.write("{} <-> {} <-> {}\n".format(z.name, tn, rn))
	
	def zeige_zeit(self):
		p = self.problem
		topr = PrettyTable(["Zeit","Thema","Betreuer","Raum"])
		for z in p.zeiteinheiten:
			for t in p.themen:
				if self.raum_von[t,z]:
					topr.add_row([z.name,t.titel,self.betreuer_von[t,z].cname(),self.raum_von[t,z].name])
		print(topr)
	
	def zeige_betreuer(self):
		p = self.problem
		topr = PrettyTable(["Betreuer", "Zeit", "Thema", "Raum", "Präferenz"])
		for b in p.betreuer:
			for z in p.zeiteinheiten:
				t = self.betreuer_stundenplan[b,z]
				if t:
					topr.add_row([b.cname(), z.stelle, t.titel, self.raum_von[t,z].name, p.pref[b,t]])
				else:
					topr.add_row([b.cname(), z.stelle, "" if not p.istda[b,z] else "---", "", ""])
		print(topr)
	
	def zeige_thema(self):
		p = self.problem
		topr = PrettyTable(["ID","Thema","Zeiten","Betreuer","Benötigt","Beliebtheit","# Kompetente"])
		for t in p.themen:
			topr.add_row([t.id,t.titel," ".join([str(z.stelle) for z in p.zeiteinheiten if self.betreuer_von[t,z]]) ,", ".join([b.cname() for b in p.betreuer if self.betreuer_themen[b,t]])," ".join([str(v.id) for v in p.thema_voraussetzungen[t]]), "%.1f" % p.thema_beliebtheit[t], len([1 for s in p.schueler if p.pref[s,t] == -1])])
		print(topr)
	
	def zeige_raum(self):
		p = self.problem
		topr = PrettyTable(["Zeit","Freie Nicht-Spezial-Räume"])
		for z in p.zeiteinheiten:
			topr.add_row([z.name, ", ".join("{} ({})".format(r.name, r.id) for r in p.raeume if sum(self.raum_belegungen[r,t,z] for t in p.themen) == 0 and r.themen_id is None)])
		print(topr)
