#!/usr/bin/python
# -*- coding: utf-8 -*-

import pulp
import subprocess
from prettytable import PrettyTable # Das ist ein Pythonpaket
from inputs import Bessere, PulpMatrix, lpsolver
import os

# Wandelt den String a in ein für eine TeX-Datei passendes Format um
def tex(a):
	a = a.replace(r"""<br />"""+"\n"+r"""Mehr dazu <a href="/content/exkursionen-0">hier</a>.""","")
	a = a.replace("_","\\_").replace("&","\\&").replace("<p>","").replace("</p>","").replace("<br />","\\newline")
	a = a.replace("<ul>", r"\begin{itemize}\itemsep1pt \parskip0pt \parsep0pt")
	a = a.replace("</ul>", r"\end{itemize}")
	a = a.replace("<li>", r"\item ")
	a = a.replace("</li>", "")
	a = a.replace("""<a href="http://www.orpheus-verein.de/sites/default/files/OSZ.pdf">http://www.orpheus-verein.de/sites/default/files/OSZ.pdf</a>""", "http://www.orpheus-verein.de/sites/default/files/OSZ.pdf")
	a = a.replace("->", r" $\rightarrow$")
	a = a.replace("”", "\"")
	a = a.replace("Einladung zum Vereinstreffen 2014", "Einladung zum Vereinstreffen 2014: Das nächste Vereinstreffen findet vom 2. bis 5. Januar 2014 in München statt, Anmeldung voraussichtlich ab Mitte Oktober möglich. Neben einer offiziellen Mitgliederversammlung und neuen Bekanntschaften erwartet Dich dort u.a. das größte technisch-naturwissenschaftliche Museum der Welt! Mehr Informationen gibt es bald auf der Vereinshomepage www.orpheus-verein.de")
	b = ""
	anf = 0
	for i in range(len(a)):
		if a[i] == "\"":
			if anf%2 == 0:
				b += "\"`"
			else:
				b += "\"'"
			anf += 1
		else:
			b += a[i]
	return b

class Lokal(object):
	def __init__(self, problem, glob):
		self.problem = problem
		self.glob = glob
	
	def _calculate(self):
		p = self.problem
		gl = self.glob
		
		prob = pulp.LpProblem("Stundenplan", pulp.LpMaximize)
		belegungen = PulpMatrix("belegungen", (p.schueler, p.themen, p.zeiteinheiten), 0, 1, pulp.LpInteger)
		
		# TODO Einige Bedingungen müssten noch mal überdacht werden.
		
		# Ein Schüler besucht pro Zeiteinheit höchstens eine Veranstaltung und das auch nur, wenn er da ist
		# Ein Schüler kann zu einer Zeit im Prinzip frei haben (wird Langeweile genannt), das wird aber sehr vermieden (hohe Strafe in der Bewertungsfunktion)
		schuelerlangeweile = PulpMatrix("schuelerlangeweile", (p.schueler,), 0, None, pulp.LpInteger)
		leerlauf = PulpMatrix("leerlauf", (p.schueler,p.zeiteinheiten), 0, 1, pulp.LpInteger)
		for a in p.schueler:
			for z in p.zeiteinheiten:
				prob += leerlauf[a,z] == p.istda[a, z] - pulp.lpSum([ belegungen[a, t, z] for t in p.themen ])
			prob += schuelerlangeweile[a] == pulp.lpSum(leerlauf[a,z] for z in p.zeiteinheiten)
			prob += schuelerlangeweile[a] <= 1#FIXME
			prob += schuelerlangeweile[a] == 0#FIXME
		langeweile_malus = pulp.lpSum(-schuelerlangeweile[a] for a in p.schueler)
		print(1)
		
		# Ob der Schüler das Thema besucht (automatisch höchstens einmal)
		schuelerthemen = PulpMatrix("schuelerthemen", (p.schueler, p.themen), 0, 1, pulp.LpInteger)
		for a in p.schueler:
			for t in p.themen:
				if t.laenge == 1:
					prob += schuelerthemen[a,t] == pulp.lpSum(belegungen[a,t,z] for z in p.zeiteinheiten)
				elif t.laenge ==2:
					gleich_sequel = False
					for z, fortsetzung_z in zip(p.zeiteinheiten[:-1], p.zeiteinheiten[1:]):
						if sum(gl.raum_belegungen[r,t,z] for r in p.raeume) > 0:
							if not gleich_sequel:
								prob += belegungen[a,t,z] == belegungen[a,t,fortsetzung_z]
							gleich_sequel = not gleich_sequel
					prob += schuelerthemen[a,t]*2 == pulp.lpSum(belegungen[a,t,z] for z in p.zeiteinheiten) #TODO Funktioniert das?
		print(2)
		
		# Thema darf nur belegt werden, wenn ein Raum dafür belegt ist, und dann auch nur in der maximalen Anzahl Personen
		#maxauslastung = pulp.LpVariable("maxauslastung", 0, None, pulp.LpContinuous)
		for z in p.zeiteinheiten:
			for t in p.themen:
				#prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= sum([min(r.max_personen,15) * gl.raum_belegungen[r,t,z] for r in p.raeume]) #TODO wieso hier minimum 15?
				prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= sum([min(r.max_personen,30) * gl.raum_belegungen[r,t,z] for r in p.raeume]) #TODO Simeon empfiehlt max 30 Personen
				#prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= sum([r.max_personen * gl.raum_belegungen[r,t,z] for r in p.raeume])
				#prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= maxauslastung * sum([gl.raum_belegungen[r,t,z] for r in p.raeume])
				# Jede Veranstaltung soll von >= 2 Leuten besucht werden (POTENTIELL GEFÄHRLICH!!!)
				mingroesse = 3
				for r in p.raeume:
					if r.themen_id == t.id:
						mingroesse = 4
		# FIXME Große Räume sollten ein bisschen mehr ausgelastet werden (Simeon)
					if r.max_personen > 40:
						mingroesse = 6
				prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) >= sum([mingroesse * gl.raum_belegungen[r,t,z] for r in p.raeume])
		print(3)
		
		#prob += maxauslastung <= 15 # SEHR SELTSAM, dass das die Sache verbessert!!!
		
		# Was für Themen der Schüler zu welchen Zeitpunkten hatte
		kennt_thema = PulpMatrix("kennt_thema", (p.schueler, p.themen, p.zeiteinheiten), 0, None, pulp.LpInteger)
		for s in p.schueler:
			for t in p.themen:
				vorher = 0
				for z in p.zeiteinheiten:
					prob += kennt_thema[s,t,z] == vorher + belegungen[s,t,z]
					vorher = kennt_thema[s,t,z]
		print(4)
		
		# Ein Schüler muss alle Voraussetzungen kennen
		for t in p.themen:
			for v in p.thema_voraussetzungen[t]:
				for s in p.schueler:
					for z in p.zeiteinheiten:
						if p.pref[s,t] >= 0 and p.pref[s,v] != -1:
							prob += belegungen[s,t,z] <= kennt_thema[s,v,z]
		print(5)
		

		# Gerne = -1 oder 0 => Der Schüler will das Thema auf keinen Fall
		# TODO Sollte das wirklich rein?
		for a in p.schueler:
			for t in p.themen:
				if p.pref[a,t] in (0,-1):
					#prob += schuelerthemen[a,t] == 0 # == 0 klappt leider nicht immer FIXME
		falsche_themen = pulp.lpSum([-schuelerthemen[a,t] for a in p.schueler for t in p.themen if p.pref[a,t] == -1])
		
		# Die Funktion, nach der optimiert wird
		# TODO Vielleicht "gerne == -1" stärker bestrafen
		schuelerphysikspass = Bessere((p.schueler,), 0)
		min_spass = pulp.LpVariable("min_spass", 0, None, pulp.LpContinuous)
		for s in p.schueler:
			schuelerphysikspass[s] = pulp.lpSum([schuelerthemen[s,t]*p.prefbetter[s,t] for t in p.themen])
			prob += schuelerphysikspass[s] >= min_spass
			#prob += min_spass >= 0.6 #FIXME
		physikspass = pulp.lpSum([schuelerphysikspass[s] for s in p.schueler])
		print(6)
		
		
		# Sicherstellen, dass jeder genügend Experimente bekommt, wenn er sie will
		experimente = PulpMatrix("experimente", (p.schueler,), 0, None, pulp.LpInteger)
		for s in p.schueler:
			prob += experimente[s] == pulp.lpSum([belegungen[s,t,z] for t in p.themen for z in p.zeiteinheiten if t.typ == "Experiment"])
			experimente_die_s_will = len([e for e in p.themen if e.typ == "Experiment" and p.pref[s,t] > 0])
			prob += experimente[s] >= min(2,experimente_die_s_will)
		#physikspass = pulp.LpVariable("physikspass", 0, None, pulp.LpContinuous)
		#for a in p.schueler:
			#prob += pulp.lpSum([schuelerthemen[a,t]*p.prefbetter[a,t] for t in p.themen]) >= physikspass
		
		#groessenbewertung = PulpMatrix("groessenbewertung", (p.themen,p.zeiteinheiten), 0, None, pulp.LpInteger)
		#for t in p.themen:
			#for z in p.zeiteinheiten:
				#prob += groessenbewertung[t,z] >= pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) - t.gutegroesse()*sum([gl.raum_belegungen[r,t,z] for r in p.raeume])
		print(7)
		
		prob += physikspass + 10*langeweile_malus + 30*falsche_themen + 5000*len(p.schueler)*min_spass #- 0.5*maxauslastung #+ pulp.lpSum([-groessenbewertung[t,z] for t in p.themen for z in p.zeiteinheiten])
		print(8)
		
		# TODO Gerechtigkeit
		
		#prob.writeLP("lokal.lp")
		#print 9
		#prob.writeMPS("lokal.mps")
		#print 10
		if prob.solve(lpsolver()) != 1:
			raise BaseException("Konnte das Optimierungsproblem nicht lösen")
		
		self.belegungen = belegungen.werte()
		
		print("Langeweile = {}".format(pulp.value(langeweile_malus)))
		print("objective = {}".format(pulp.value(prob.objective)))
		
		self.calcrest()
	
	def calcrest(self):
		p = self.problem
		gl = self.glob
		self.stundenplan = Bessere((p.betreuer+p.schueler,p.zeiteinheiten), None)
		self.teilnehmer_von = Bessere((p.themen,p.zeiteinheiten), [])
		self.machtthema = Bessere((p.schueler,p.themen), None)
		for b in p.betreuer:
			for z in p.zeiteinheiten:
				self.stundenplan[b,z] = gl.betreuer_stundenplan[b,z]
		for s in p.schueler:
			for z in p.zeiteinheiten:
				for t in p.themen:
					if self.belegungen[s,t,z]:
						self.stundenplan[s,z] = t
						self.teilnehmer_von[t,z].append(s)
						self.machtthema[s,t] = 1
	
	@classmethod
	def calculate(cls, problem, glob):
		x = cls(problem, glob)
		x._calculate()
		return x
	
	def _load(self, filename):
		p = self.problem
		gl = self.glob
		self.belegungen = Bessere((p.schueler,p.themen,p.zeiteinheiten), 0)
		gefundene_schueler = set()
		with open(filename) as f:
			while True:
				line = f.readline()
				if line == "":
					break
				line = line.replace("\n","")
				if line == "" or line[0] == "#":
					continue
				if line[0:2] != "= ":
					raise ValueError("Schüler erwartet")
				line = line[2:]
				s = None
				for ss in p.schueler:
					if ss.cname() == line:
						s = ss
				if s is None:
					raise ValueError("Schüler \"{}\" existiert nicht".format(line))
				if s.id in gefundene_schueler:
					raise ValueError("Schüler \"{}\" schon angegeben".format(line))
				gefundene_schueler.add(s.id)
				for z in p.zeiteinheiten:
					line = f.readline()
					if line == "":
						raise ValueError("Was macht Schüler \"{}\" zur Zeit \"{}\"?".format(s.cname(),z.name))
					line = line.replace("\n","")
					line = line.split(" <-> ")
					if len(line) != 2:
						raise ValueError("Falsches Format für Schüler \"{}\" zur Zeit \"{}\"".format(s.cname(),z.name))
					if line[0] != z.name:
						raise ValueError("Falsche Zeit \"{}\" für Schüler \"{}\" (wollte \"{}\")".format(line[0],s.cname(),z.name))
					if line[1] == "":
						continue
					t = None
					for ts in p.themen:
						if ts.titel == line[1]:
							t = ts
					if t is None:
						raise ValueError("Thema \"{}\" existiert nicht (für Schüler \"{}\" zu Zeit \"{}\")".format(line[1],s.cname(),z.name))
					self.belegungen[s,t,z] = 1
		if len(gefundene_schueler) < len(p.schueler):
			raise ValueError("Nicht alle Schüler angegeben")
		# Ein Schüler besucht pro Zeiteinheit höchstens eine Veranstaltung und das auch nur, wenn er da ist
		for s in p.schueler:
			for z in p.zeiteinheiten:
				if sum([ self.belegungen[s,t,z] for t in p.themen ]) > p.istda[s,z]:
					raise ValueError("Schüler {} macht zur Zeit {} mehr als möglich (weil er nicht da ist?)".format(s.cname(),z.name))
		# Ein Schüler besucht jedes Thema höchstens einmal
		for s in p.schueler:
			for t in p.themen:
				if sum([self.belegungen[s,t,z] for z in p.zeiteinheiten]) > t.laenge:
					raise ValueError("Schüler {} besucht Thema {} mehrmals".format(s.cname(),t.titel))
		# Thema darf nur belegt werden, wenn ein Raum dafür belegt ist, und dann auch nur in der maximalen Anzahl Personen
		for z in p.zeiteinheiten:
			for t in p.themen:
				#if sum([self.belegungen[s,t,z] for s in p.schueler]) > sum([min(r.max_personen,15) * gl.raum_belegungen[r,t,z] for r in p.raeume]):
				if sum([self.belegungen[s,t,z] for s in p.schueler]) > sum([r.max_personen * gl.raum_belegungen[r,t,z] for r in p.raeume]):
					raise ValueError("Thema {} ist zur Zeit {} überbelegt".format(t.titel,z.name))
				# Jede Veranstaltung soll von >= 2 Leuten besucht werden (POTENTIELL GEFÄHRLICH!!!)
				if sum([self.belegungen[s,t,z] for s in p.schueler]) < sum([2 * gl.raum_belegungen[r,t,z] for r in p.raeume]):
					raise ValueError("Thema {} ist zur Zeit {} unterbelegt".format(t.titel,z.name))
		# Was für Themen der Schüler zu welchen Zeitpunkten hatte
		kennt_thema = Bessere((p.schueler, p.themen, p.zeiteinheiten), 0)
		for s in p.schueler:
			for t in p.themen:
				vorher = 0
				for z in p.zeiteinheiten:
					kennt_thema[s,t,z] = vorher + self.belegungen[s,t,z]
					vorher = kennt_thema[s,t,z]
		# Ein Schüler muss alle Voraussetzungen kennen
		for t in p.themen:
			for v in p.thema_voraussetzungen[t]:
				for s in p.schueler:
					if s.id == 960 and t.id==306: #Daniel Petersen
						print(t.titel, v.titel)
						for z in p.zeiteinheiten:
							print(self.belegungen[s,t,z], kennt_thema[s,v,z], p.pref[s,t], p.pref[s,v], z.name)
					for z in p.zeiteinheiten:
						if p.pref[s,t] >= 1 and p.pref[s,v] != -1:
							if self.belegungen[s,t,z] > kennt_thema[s,v,z]:
								raise ValueError("Schüler {} muss zuerst Voraussetzung {} für {} lernen".format(s.cname(),v.titel,t.titel))
		self.calcrest()
	
	@classmethod
	def load(cls, problem, glob):
		x = cls(problem, glob)
		x._load("results/{}/Lokal.txt".format(problem.problem_id))
		return x
	
	def save(self):
		p = self.problem
		with open("results/{}/Lokal.txt".format(p.problem_id),"w") as f:
			f.write("# Du darfst diese Datei editieren um den Stundenplan zu ändern\n")
			for s in p.schueler:
				f.write("= {}\n".format(s.cname()))
				for z in p.zeiteinheiten:
					t = self.stundenplan[s,z]
					tn = t.titel if t is not None else ""
					f.write("{} <-> {}\n".format(z.name, tn))
	
	def zeige_zeit(self):
		p = self.problem
		gl = self.glob
		topr = PrettyTable(["Zeit", "Thema", "Betreuer", "Raum", "# Teilnehmer"])
		for z in p.zeiteinheiten:
			for t in p.themen:
				if gl.raum_von[t,z]:
					topr.add_row([z.stelle, t.titel, gl.betreuer_von[t,z].cname(), gl.raum_von[t,z].name, len(self.teilnehmer_von[t,z])])
		print(topr)
	
	def zeige_schueler(self):
		p = self.problem
		gl = self.glob
		topr = PrettyTable(["Schüler", "Zeit", "Thema", "Raum", "Präferenz"])
		for s in p.schueler:
			for z in p.zeiteinheiten:
				t = self.stundenplan[s,z]
				if t:
					topr.add_row([s.cname(), z.name, t.titel, gl.raum_von[t,z].name, p.pref[s,t]])
				else:
					topr.add_row([s.cname(), z.name, "", "", ""])
		print(topr)
	
	def zeige_thema(self):
		p = self.problem
		gl = self.glob
		topr = PrettyTable(["ID","Thema","Zeiten","Betreuer","Benötigt","Beliebtheit","# Komp.","# Teilnehmer", "ges. # T."])
		for t in p.themen:
			topr.add_row([t.id,t.titel," ".join([str(z.stelle) for z in p.zeiteinheiten if gl.betreuer_von[t,z]]) ,", ".join([b.cname() for b in p.betreuer if gl.betreuer_themen[b,t]])," ".join([str(v.id) for v in p.thema_voraussetzungen[t]]), "%.1f" % p.thema_beliebtheit[t], len([1 for s in p.schueler if p.pref[s,t] == -1])," ".join([ str(len(self.teilnehmer_von[t,z])) for z in p.zeiteinheiten if gl.betreuer_von[t,z]]),sum([ len(self.teilnehmer_von[t,z]) for z in p.zeiteinheiten if gl.betreuer_von[t,z]])])
		print(topr)
	
	def zeige_guete(self):
		p = self.problem
		gl = self.glob
		
		anzpref = {-1:0,0:0,1:0,2:0,3:0,"Langeweile":0}
		for z in p.zeiteinheiten:
			for a in p.schueler:
				if self.stundenplan[a,z]:
					anzpref[p.pref[a,self.stundenplan[a,z]]] += 1
				elif p.istda[a,z]:
					anzpref["Langeweile"] += 1
		
		gesamtspass = 0
		
		spass = Bessere((p.schueler,), 0)
		for s in p.schueler:
			spass[s] = sum([p.prefbetter[s,t] for t in p.themen if self.machtthema[s,t]])
			gesamtspass += spass[s]
		prefs = range(-1,4)
		topr = PrettyTable(["Teilnehmer","Spaß","Langeweile"]+list(map(str, prefs)))
		def vorkommen(pref):
			return str(len([t for t in p.themen if p.pref[s,t]==pref and self.machtthema[s,t]]))
		for s in sorted(p.schueler, key=lambda s : spass[s]):
			topr.add_row([s.cname(), "%.2f" % spass[s], len([1 for z in p.zeiteinheiten if p.istda[s,z] and not self.stundenplan[s,z]])] + list(map(vorkommen, prefs)))
		print(topr)
		
		topr = PrettyTable(["Präferenz","Anzahl"])
		for g in ["Langeweile",-1,0,1,2,3]:
			topr.add_row([g,anzpref[g]])
		print(topr)
		
		print("Gesamter Spaß: %.2f" % gesamtspass)
	
	def mache_kursplan_tex(self):
		p = self.problem
		gl = self.glob
		with open("kursplan.tex", encoding="utf8") as f:
			template = f.read()
		with open("kursplan-zeit.tex", encoding="utf8") as f:
			stemplate = f.read()
		eersetzen = {"themen": ""}
		for t in p.themen:
			eersetzen["themen"] += "\\thema{%s}{%s}\n" % (tex(t.titel), tex(t.beschreibung))
		for z in p.zeiteinheiten:
			ersetzen = {"name": z.name, "kursliste": ""}
			for t in p.themen:
				if gl.raum_von[t,z]:
					ersetzen["kursliste"] += "\\hline\n%s&%s&%s&%d\\\\\n" % (tex(t.titel), tex(gl.betreuer_von[t,z].cname()), tex(gl.raum_von[t,z].name), len(self.teilnehmer_von[t,z]))
			eersetzen["plan%d" % z.stelle] = stemplate % ersetzen
		with open("results/{}/kursplan-ergebnis.tex".format(p.problem_id), "w", encoding="utf8") as f:
			f.write((template % eersetzen))
		#subprocess.call(["latexmk","-pdf","kursplan-ergebnis.tex","-silent"]) #WAS IST DAS DENN
		os.chdir("results/{}".format(p.problem_id))
		subprocess.call(["pdflatex", "kursplan-ergebnis.tex", "-silent"])
		os.chdir("../..")
	
	def mache_stundenplaene_tex(self):
		p = self.problem
		gl = self.glob
		schuelerplaene = ""
		with open("stundenplan.tex", encoding="utf8") as stundenplan_datei:
			template = stundenplan_datei.read()
		with open("stundenplan-einzeln.tex", encoding="utf8") as stundenplan_einzeln_datei:
			stemplate = stundenplan_einzeln_datei.read()
		for a in sorted(p.schueler, key=lambda b: b.name)+sorted(p.betreuer, key=lambda b: b.name):
			ersetzen = {"name": a.cname(), "betreuerpagebreak": "", "betreuerkeinpagebreak": r"\newpage" if a not in p.betreuer else ""}
			#ersetzen = {"name": a.cname(), "betreuerpagebreak": r"\newpage" if a in p.betreuer else "", "betreuerkeinpagebreak": r"\newpage" if a not in p.betreuer else ""}
			def convert(n):
				n = n.replace("Do ", "")
				n = n.replace("Fr ", "")
				n = n.replace("Sa ", "")
				n = n.replace("So ", "")
				if n[1] == ':':
					n = "\\phantom{1}"+tex(n)
				return n
			for i, z in enumerate(p.zeiteinheiten):
				if self.stundenplan[a,z]:
					t = self.stundenplan[a,z]
					tn = t.titel
					if t.laenge == 2 and i > 0:
						if self.stundenplan[a,p.zeiteinheiten[i-1]] == t:
							tn += " (Fortsetzung)"
					rn = gl.raum_von[t,z].name
					beschr = "ca. %d Teilnehmer" % len(self.teilnehmer_von[t,z])
					if a in p.betreuer:
						beschr += ": " + ", ".join(s.cname() for s in self.teilnehmer_von[t,z])
					else:
						beschr += ", Betreuer: "+gl.betreuer_von[t,z].cname()
				else:
					tn = "frei"
					rn = ""
					beschr = ""
				if a in p.betreuer:
					if beschr != "":
						beschr += "\\newline\n"
					beschr += "Folgende Betreuer haben frei: " + ", ".join(b.cname() for b in p.betreuer if gl.betreuer_stundenplan[b,z] is None and p.istda[b,z])
				if beschr != "":
					beschr = "\n\n\\beschreibung{%s}" % beschr
				ersetzen["kurs%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}%s}" % (convert(z.name), tex(tn), tex(rn), beschr)
			for z in p.nichtphysikzeiteinheiten:
				if z == p.exkursionenzeit:
					ersetzen["nichtphysik%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}\n\n\\beschreibung{%s}}" % (convert(z.name), tex("Exkursion: "+p.exkursionenzuordnung[a].titel if p.exkursionenzuordnung[a] else "frei"), "", "ca. %d Teilnehmer" % p.exkursionenfuelle[p.exkursionenzuordnung[a]])
				elif z.beschreibung != "":
					ersetzen["nichtphysik%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}\n\n\\beschreibung{%s}}" % (convert(z.name), tex(z.titel), tex(z.ort), tex(z.beschreibung))
				else:
					ersetzen["nichtphysik%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}}" % (convert(z.name), tex(z.titel), tex(z.ort))
			schuelerplaene += stemplate % ersetzen
		with open("results/{}/stundenplaene-ergebnis.tex".format(p.problem_id), "w", encoding="utf8") as f:
			f.write((template % {"schueler": schuelerplaene}))
		os.chdir("results/{}".format(p.problem_id))
		subprocess.call(["pdflatex", "stundenplaene-ergebnis.tex".format(p.problem_id), "-silent"])
		os.chdir("../..")
