#!/usr/bin/python2
# -*- coding: utf-8 -*-

import pulp
from prettytable import PrettyTable # Das ist ein Pythonpaket
from problem import Bessere, PulpMatrix, lpsolver, Problem

# Speichert eine Lösung des globalen Stundenplanproblems (wann hält welcher Betreuer welches Thema wo?)
class Global:
	def __init__(self, problem):
		self.problem = problem
	
	def _calculate(self):
		p = self.problem
		prob = pulp.LpProblem("Stundenplan", pulp.LpMaximize)
		
		raum_belegungen = PulpMatrix("raum_belegungen", (p.raeume, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		
		# Raum nur benutzen, wenn er verfügbar ist (insbesondere zu jedem Zeitpunkt nur höchstens einmal)
		for r in p.raeume:
			for z in p.zeiteinheiten:
				prob += pulp.lpSum([raum_belegungen[r,t,z] for t in p.themen]) <= p.raumverfuegbar[r,z]
		
		# Dadurch wird automatisch pro (Thema, Zeit) nur ein Raum belegt
		thema_findet_dann_statt = PulpMatrix("thema_findet_dann_statt", (p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for t in p.themen:
			for z in p.zeiteinheiten:
				prob += thema_findet_dann_statt[t,z] == pulp.lpSum([raum_belegungen[r,t,z] for r in p.raeume])
		
		# Dafür sorgen, dass es genug Kurse für alle gibt
		for z in p.zeiteinheiten:
			prob += pulp.lpSum([raum_belegungen[r,t,z]*r.max_personen for t in p.themen for r in p.raeume]) >= sum([p.istda[s,z] for s in p.schueler])-10
		
		# Spezialräume
		nurinraeumen = Bessere((p.themen,), [])
		for r in p.raeume:
			if r.themen_id: # Der Raum ist für ein spezielles Thema vorgesehen
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
		
		
		print("Betreuer")
		betreuer_belegungen = PulpMatrix("betreuer_belegungen", (p.betreuer, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for z in p.zeiteinheiten:
			for b in p.betreuer:
				# Jeder Betreuer kann pro Zeit nur ein Thema betreuen
				prob += pulp.lpSum([betreuer_belegungen[b,t,z] for t in p.themen]) <= 1
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
				if p.pref[b,t] == 2: # Unbedingt und sonst niemand
					# Das bedeutet, dass jedes Thema, das jemand unbedingt machen will, irgendwann angeboten wird (TODO so OK?)
					prob += betreuer_themen[b,t] == 1
					for ab in p.betreuer:
						if ab.id != b.id:
							prob += betreuer_themen[ab,t] == 0
				elif p.pref[b,t] == -1: # Auf keinen Fall
					prob += betreuer_themen[b,t] == 0
		
		thema_findet_so_oft_statt = PulpMatrix("thema_findet_so_oft_statt", (p.themen,), 0, None, pulp.LpInteger)
		for t in p.themen:
			prob += thema_findet_so_oft_statt[t] == pulp.lpSum([thema_findet_dann_statt[t,z] for z in p.zeiteinheiten])
		
		# Mikhails hardgecodet:
		prob += betreuer_belegungen[p.mikhail,p.mikhail_1,10] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_2,11] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_3,12] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_4,13] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_1,14] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_2,15] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_3,16] == 1
		prob += betreuer_belegungen[p.mikhail,p.mikhail_4,17] == 1
		
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
			
		#TODO: Bei Bedarf hier noch Schranken auf thema_findet_so_oft_statt
		
		print("Optimierung")
		guete = PulpMatrix("guete", (p.themen,p.zeiteinheiten), 0, 1, pulp.LpContinuous)
		for g in p.gebiete:
			if t in p.verwendende[g]:
				for z2 in p.zeiteinheiten:
					#varr = pulp.LpVariable("guete_helferr_{}_{}_{}".format(t.id, z2.id, g.id), 0, 1, pulp.LpInteger)
					#prob += varr <= pulp.lpSum([thema_findet_dann_statt[b,z1] for b in p.beibringende[g] for z1 in p.zeiteinheiten if z1.stelle < z2.stelle])
					#prob += guete[t,z2] <= p.durchschnittskompetenz[g]+(1-p.durchschnittskompetenz[g])*varr
					guete[t,z2] <= pulp.lpSum([thema_findet_dann_statt[b,z1]*t.gutegroesse() for b in p.beibringende[g] for z1 in p.zeiteinheiten if z1.stelle < z2.stelle])
		
		#for t in p.themen:
			#for g in p.gebiete:
				#if t in p.beibringende[g]:
					##prob += pulp.lpSum([z.stelle*thema_findet_dann_statt[t,z] for z in p.zeiteinheiten]) <= 4*thema_findet_so_oft_statt[t]
					#prob += pulp.lpSum([z.stelle*thema_findet_dann_statt[t,z] for z in p.zeiteinheiten if z.stelle <= 4]) >= 1
		
		platz = PulpMatrix("platz", (p.themen,p.zeiteinheiten), 0, None, pulp.LpContinuous)
		for t in p.themen:
			for z in p.zeiteinheiten:
				prob += platz[t,z] <= thema_findet_dann_statt[t,z]*t.gutegroesse()
				#prob += platz[t,z] <= guete[t,z]*t.gutegroesse()
				prob += platz[t,z] <= guete[t,z]
		
		ueberfuellung = PulpMatrix("ueberfuellung", (p.themen,), 0, None, pulp.LpContinuous)
		for t in p.themen:
			prob += ueberfuellung[t] >= p.thema_beliebtheit[t] - pulp.lpSum([platz[t,z] for z in p.zeiteinheiten])
		
		beliebtheit = pulp.lpSum([-ueberfuellung[t] for t in p.themen])
		
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
		
		gesamtangebot = pulp.lpSum([thema_findet_dann_statt[t,z] for t in p.themen for z in p.zeiteinheiten])
		
		#reihenfolge = []
		#for g in p.gebiete:
			#for t1 in p.beibringende[g]:
				#for t2 in p.verwendende[g]:
					#for z1 in p.zeiteinheiten:
						#for z2 in p.zeiteinheiten:
							#var = pulp.LpVariable("reihenfolge_helfer_{}_{}_{}".format(t1.id, t2.id, z1.id, z2.id), 0, 1, pulp.LpInteger)
							#prob += var <= thema_findet_dann_statt[t1,z1]
							#prob += var <= thema_findet_dann_statt[t2,z2]
							#reihenfolge.append(var)
		#reihenfolge = pulp.lpSum(reihenfolge)
		
		# Die gewichtete Optimierungsfunktion:
		prob += beliebtheit + gesamtangebot #+ 0.01*reihenfolge #+ (-0.5)*korrelationsmalus
		
		# Gerechtigkeitsdummys
		# Dummybedingungen um Fehler zu finden. Außerdem ist das eigentlich relativ gerecht.
		# Jeder Betreuer sollte mindestens 5 Mal etwas tun
		for b in p.betreuer:
			prob += pulp.lpSum([betreuer_belegungen[b,t,z] for t in p.themen for z in p.zeiteinheiten]) >= 5
		# Jeder Betreuer sollte mindestens 2 verschiedene Themen haben
		for b in p.betreuer:
			prob += pulp.lpSum([betreuer_themen[b,t] for t in p.themen]) >= 2
		
		#prob.writeLP("global.lp")
		#prob.writeMPS("global.mps")
		if prob.solve(lpsolver()) != 1:
			raise BaseException("Konnte das Optimierungsproblem nicht lösen")
		
		self.raum_belegungen = raum_belegungen.werte()
		self.betreuer_themen = betreuer_themen.werte()
		self.betreuer_belegungen = betreuer_belegungen.werte()
		
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
				line = line.decode("utf8").replace("\n","")
				if line == "" or line[0] == "#":
					continue
				if line[0:2] != "= ":
					raise Exception(u"Betreuer erwartet")
				line = line[2:]
				b = None
				for bs in p.betreuer:
					if bs.cname() == line:
						b = bs
				if b is None:
					raise Exception(u"Betreuer \"{}\" existiert nicht".format(line).encode("utf8"))
				if b.id in gefundene_betreuer:
					raise Exception(u"Betreuer \"{}\" schon angegeben".format(line).encode("utf8"))
				gefundene_betreuer.add(b.id)
				for z in p.zeiteinheiten:
					line = f.readline()
					if line == "":
						raise Exception(u"Was macht Betreuer \"{}\" zur Zeit \"{}\"?".format(b.cname(),z.name).encode("utf8"))
					line = line.decode("utf8").replace("\n","")
					line = line.split(" <-> ")
					if len(line) != 3:
						raise Exception(u"Falsches Format für Betreuer \"{}\" zur Zeit \"{}\"".format(b.cname(),z.name).encode("utf8"))
					if line[0] != z.name:
						raise Exception(u"Falsche Zeit \"{}\" für Betreuer \"{}\" (wollte \"{}\")".format(line[0],b.cname(),z.name).encode("utf8"))
					if line[1] == "" and line[2] == "":
						continue
					t = None
					for ts in p.themen:
						if ts.titel == line[1]:
							t = ts
					if t is None:
						raise Exception(u"Thema \"{}\" existiert nicht (für Betreuer \"{}\" zu Zeit \"{}\")".format(line[1],b.cname(),z.name).encode("utf8"))
					r = None
					for rs in p.raeume:
						if rs.name == line[2]:
							r = rs
					if r is None:
						raise Exception(u"Raum \"{}\" existiert nicht (für Betreuer \"{}\" zu Zeit \"{}\")".format(line[2],b.cname(),z.name).encode("utf8"))
					self.raum_belegungen[r,t,z] = 1
					self.betreuer_themen[b,t] = 1
					self.betreuer_belegungen[b,t,z] = 1
		if len(gefundene_betreuer) < len(p.betreuer):
			raise Exception(u"Nicht alle Betreuer angegeben")
		self.calcrest()
		# TODO Haufenweise Konsistenzchecks (ungefähr wie die Bedingungen in calculate)
	
	@classmethod
	def load(cls, problem, filename):
		x = cls(problem)	
		x._load(filename)
		return x
	
	def save(self, filename):
		p = self.problem
		with open(filename,"w") as f:
			f.write("# Du darfst diese Datei editieren um den Stundenplan zu ändern\n")
			for b in p.betreuer:
				f.write(u"= {}\n".format(b.cname()).encode("utf8"))
				for z in p.zeiteinheiten:
					t = self.betreuer_stundenplan[b,z]
					tn = t.titel if t is not None else ""
					r = self.betreuer_raumplan[b,z]
					rn = r.name if r is not None else ""
					f.write(u"{} <-> {} <-> {}\n".format(z.name, tn, rn).encode("utf8"))
	
	def zeige_zeit(self):
		p = self.problem
		topr = PrettyTable(["Zeit","Thema","Betreuer","Raum"])
		for z in p.zeiteinheiten:
			for t in p.themen:
				if self.raum_von[t,z]:
					topr.add_row([z.name,t.titel,self.betreuer_von[t,z].cname(),self.raum_von[t,z].name])
		print topr
	
	def zeige_betreuer(self):
		p = self.problem
		topr = PrettyTable(["Betreuer", "Zeit", "Thema", "Raum", "Präferenz"])
		for b in p.betreuer:
			for z in p.zeiteinheiten:
				t = self.betreuer_stundenplan[b,z]
				if t:
					topr.add_row([b.cname(), z.stelle, t.titel, self.raum_von[t,z].name, p.pref[b,t]])
				else:
					topr.add_row([b.cname(), z.stelle, "", "", ""])
		print topr
	
	def zeige_thema(self):
		p = self.problem
		topr = PrettyTable(["Thema","Zeiten","Betreuer","Benötigt","Bringt bei","Beliebtheit"])
		for t in p.themen:
			topr.add_row([t.titel," ".join([str(z.stelle) for z in p.zeiteinheiten if self.betreuer_von[t,z]]) ,", ".join([b.cname() for b in p.betreuer if self.betreuer_themen[b,t]])," ".join([str(g.id) for g in p.gebiete if t in p.verwendende[g]])," ".join([str(g.id) for g in p.gebiete if t in p.beibringende[g]]), "%.1f" % p.thema_beliebtheit[t]])
		print topr
