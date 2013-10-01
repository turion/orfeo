#!/usr/bin/python2
# -*- coding: utf-8 -*-

import pulp
import subprocess
from prettytable import PrettyTable # Das ist ein Pythonpaket
from inputs import Bessere, PulpMatrix, lpsolver

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
	a = a.replace(u"”", "\"")
	b = ""
	anf = 0
	for i in xrange(len(a)):
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
		
		langeweile = []
		# Ein Schüler besucht pro Zeiteinheit höchstens eine Veranstaltung und das auch nur, wenn er da ist
		# Ein Schüler kann zu einer Zeit im Prinzip frei haben, das wird aber sehr vermieden (hohe Strafe in der Bewertungsfunktion)
		for a in p.schueler:
			zeitdavor = None
			for z in p.zeiteinheiten:
				la = pulp.lpSum([ belegungen[a, t, z] for t in p.themen ]) - p.istda[a, z]
				prob += la <= 0
				langeweile.append(1000*la)
				# Mikhail
				if zeitdavor is not None:
					prob += belegungen[a,p.mikhail_3,zeitdavor] == belegungen[a,p.mikhail_4,z]
				zeitdavor = z
		langeweile = pulp.lpSum(langeweile)
		print 1
		
		# Ob der Schüler das Thema besucht (automatisch höchstens einmal)
		schuelerthemen = PulpMatrix("schuelerthemen", (p.schueler, p.themen), 0, 1, pulp.LpInteger)
		for a in p.schueler:
			for t in p.themen:
				prob += schuelerthemen[a,t] == pulp.lpSum(belegungen[a,t,z] for z in p.zeiteinheiten)
		print 2
		
		# Thema darf nur belegt werden, wenn ein Raum dafür belegt ist, und dann auch nur in der maximalen Anzahl Personen
		#maxauslastung = pulp.LpVariable("maxauslastung", 0, None, pulp.LpContinuous)
		for z in p.zeiteinheiten:
			for t in p.themen:
				prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= sum([min(r.max_personen,12) * gl.raum_belegungen[r,t,z] for r in p.raeume])
				#prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) <= maxauslastung * sum([gl.raum_belegungen[r,t,z] for r in p.raeume])
				# Jede Veranstaltung soll von >= 2 Leuten besucht werden (POTENTIELL GEFÄHRLICH!!!)
				prob += pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) >= sum([2 * gl.raum_belegungen[r,t,z] for r in p.raeume])
		print 3
		#prob += maxauslastung <= 15 # SEHR SELTSAM, dass das die Sache verbessert!!!
		
		# Was für Themen der Schüler zu welchen Zeitpunkten hatte
		kennt_thema = PulpMatrix("kennt_thema", (p.schueler, p.themen, p.zeiteinheiten), 0, None, pulp.LpInteger)
		for s in p.schueler:
			for t in p.themen:
				vorher = 0
				for z in p.zeiteinheiten:
					prob += kennt_thema[s,t,z] == vorher + belegungen[s,t,z]
					vorher = kennt_thema[s,t,z]
		print 4
		
		# Ein Schüler muss alle Voraussetzungen kennen
		for t in p.themen:
			for v in p.thema_voraussetzungen[t]:
				for s in p.schueler:
					for z in p.zeiteinheiten:
						if p.pref[s,t] >= 1 and p.pref[s,v] != -1:
							prob += belegungen[s,t,z] <= kennt_thema[s,v,z]
		print 5
		

		# Gerne = -1 => Der Schüler will das Thema auf keinen Fall
		# TODO Sollte das wirklich rein?
		#for a in p.schueler:
			#for t in p.themen:
				#if pref[a,t] == -1:
					#prob += schuelerthemen[a,t] == 0
		
		# Die Funktion, nach der optimiert wird
		# TODO Vielleicht "gerne == -1" stärker bestrafen
		schuelerphysikspass = Bessere((p.schueler,), 0)
		for s in p.schueler:
			schuelerphysikspass[s] = pulp.lpSum([schuelerthemen[s,t]*p.prefbetter[s,t] for t in p.themen])
			prob += schuelerphysikspass[s] >= 0.7
		physikspass = pulp.lpSum([schuelerphysikspass[s] for s in p.schueler])
		print 6
		#physikspass = pulp.LpVariable("physikspass", 0, None, pulp.LpContinuous)
		#for a in p.schueler:
			#prob += pulp.lpSum([schuelerthemen[a,t]*p.prefbetter[a,t] for t in p.themen]) >= physikspass
		
		#groessenbewertung = PulpMatrix("groessenbewertung", (p.themen,p.zeiteinheiten), 0, None, pulp.LpInteger)
		#for t in p.themen:
			#for z in p.zeiteinheiten:
				#prob += groessenbewertung[t,z] >= pulp.lpSum([belegungen[a,t,z] for a in p.schueler]) - t.gutegroesse()*sum([gl.raum_belegungen[r,t,z] for r in p.raeume])
		#print 7
		
		prob += physikspass + langeweile #- 0.5*maxauslastung #+ pulp.lpSum([-groessenbewertung[t,z] for t in p.themen for z in p.zeiteinheiten])
		print 8
		
		# TODO Gerechtigkeit
		
		#prob.writeLP("lokal.lp")
		#print 9
		#prob.writeMPS("lokal.mps")
		#print 10
		if prob.solve(lpsolver()) != 1:
			raise BaseException("Konnte das Optimierungsproblem nicht lösen")
		
		self.belegungen = belegungen.werte()
		
		print "Langeweile = {}".format(pulp.value(langeweile))
		print "objective = {}".format(pulp.value(prob.objective))
		
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
				line = line.decode("utf8").replace("\n","")
				if line == "" or line[0] == "#":
					continue
				if line[0:2] != "= ":
					raise Exception(u"Schüler erwartet".encode("utf8"))
				line = line[2:]
				s = None
				for ss in p.schueler:
					if ss.cname() == line:
						s = ss
				if s is None:
					raise Exception(u"Schüler \"{}\" existiert nicht".format(line).encode("utf8"))
				if s.id in gefundene_schueler:
					raise Exception(u"Schüler \"{}\" schon angegeben".format(line).encode("utf8"))
				gefundene_schueler.add(s.id)
				for z in p.zeiteinheiten:
					line = f.readline()
					if line == "":
						raise Exception(u"Was macht Schüler \"{}\" zur Zeit \"{}\"?".format(s.cname(),z.name).encode("utf8"))
					line = line.decode("utf8").replace("\n","")
					line = line.split(" <-> ")
					if len(line) != 2:
						raise Exception(u"Falsches Format für Schüler \"{}\" zur Zeit \"{}\"".format(s.cname(),z.name).encode("utf8"))
					if line[0] != z.name:
						raise Exception(u"Falsche Zeit \"{}\" für Schüler \"{}\" (wollte \"{}\")".format(line[0],s.cname(),z.name).encode("utf8"))
					if line[1] == "":
						continue
					t = None
					for ts in p.themen:
						if ts.titel == line[1]:
							t = ts
					if t is None:
						raise Exception(u"Thema \"{}\" existiert nicht (für Schüler \"{}\" zu Zeit \"{}\")".format(line[1],s.cname(),z.name).encode("utf8"))
					self.belegungen[s,t,z] = 1
		if len(gefundene_schueler) < len(p.schueler):
			raise Exception(u"Nicht alle Schüler angegeben".encode('utf8'))
		# Ein Schüler besucht pro Zeiteinheit höchstens eine Veranstaltung und das auch nur, wenn er da ist
		for s in p.schueler:
			for z in p.zeiteinheiten:
				if sum([ self.belegungen[s,t,z] for t in p.themen ]) > p.istda[s,z]:
					raise Exception(u"Schüler {} macht zur Zeit {} mehr als möglich (weil er nicht da ist?)".format(s.cname(),z.name).encode('utf8'))
		# Ein Schüler besucht jedes Thema höchstens einmal
		for s in p.schueler:
			for t in p.themen:
				if sum([self.belegungen[s,t,z] for z in p.zeiteinheiten]) > 1:
					raise Exception(u"Schüler {} besucht Thema {} mehrmals".format(s.cname(),t.titel).encode('utf8'))
		# Thema darf nur belegt werden, wenn ein Raum dafür belegt ist, und dann auch nur in der maximalen Anzahl Personen
		for z in p.zeiteinheiten:
			for t in p.themen:
				if sum([self.belegungen[s,t,z] for s in p.schueler]) > sum([min(r.max_personen,15) * gl.raum_belegungen[r,t,z] for r in p.raeume]):
					raise Exception(u"Thema {} ist zur Zeit {} überbelegt".format(t.titel,z.name).encode('utf8'))
				# Jede Veranstaltung soll von >= 2 Leuten besucht werden (POTENTIELL GEFÄHRLICH!!!)
				if sum([self.belegungen[s,t,z] for s in p.schueler]) < sum([2 * gl.raum_belegungen[r,t,z] for r in p.raeume]):
					raise Exception(u"Thema {} ist zur Zeit {} unterbelegt".format(t.titel,z.name).encode('utf8'))
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
					for z in p.zeiteinheiten:
						if p.pref[s,t] >= 1 and p.pref[s,v] != -1:
							if self.belegungen[s,t,z] > kennt_thema[s,v,z]:
								raise Exception(u"Schüler {} muss zuert Voraussetzung {} für {} lernen".format(s.cname(),v.titel,t.titel).encode('utf8'))
		self.calcrest()
	
	@classmethod
	def load(cls, problem, glob, filename):
		x = cls(problem, glob)
		x._load(filename)
		return x
	
	def save(self, filename):
		p = self.problem
		with open(filename,"w") as f:
			f.write("# Du darfst diese Datei editieren um den Stundenplan zu ändern\n")
			for s in p.schueler:
				f.write(u"= {}\n".format(s.cname()).encode("utf8"))
				for z in p.zeiteinheiten:
					t = self.stundenplan[s,z]
					tn = t.titel if t is not None else ""
					f.write(u"{} <-> {}\n".format(z.name, tn).encode("utf8"))
	
	def zeige_zeit(self):
		p = self.problem
		gl = self.glob
		topr = PrettyTable(["Zeit", "Thema", "Betreuer", "Raum", "# Teilnehmer"])
		for z in p.zeiteinheiten:
			for t in p.themen:
				if gl.raum_von[t,z]:
					topr.add_row([z.stelle, t.titel, gl.betreuer_von[t,z].cname(), gl.raum_von[t,z].name, len(self.teilnehmer_von[t,z])])
		print topr
	
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
		print topr
	
	def zeige_thema(self):
		p = self.problem
		gl = self.glob
		topr = PrettyTable(["ID","Thema","Zeiten","Betreuer","Benötigt","Beliebtheit","# Komp.","# Teilnehmer", "ges. # T."])
		for t in p.themen:
			topr.add_row([t.id,t.titel," ".join([str(z.stelle) for z in p.zeiteinheiten if gl.betreuer_von[t,z]]) ,", ".join([b.cname() for b in p.betreuer if gl.betreuer_themen[b,t]])," ".join([str(v.id) for v in p.thema_voraussetzungen[t]]), "%.1f" % p.thema_beliebtheit[t], len([1 for s in p.schueler if p.pref[s,t] == -1])," ".join([ str(len(self.teilnehmer_von[t,z])) for z in p.zeiteinheiten if gl.betreuer_von[t,z]]),sum([ len(self.teilnehmer_von[t,z]) for z in p.zeiteinheiten if gl.betreuer_von[t,z]])])
		print topr
	
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

		topr = PrettyTable(["Präferenz","Anzahl"])
		for g in ["Langeweile",-1,0,1,2,3]:
			topr.add_row([g,anzpref[g]])
		print topr
		
		gesamtspass = 0
		
		spass = Bessere((p.schueler,), 0)
		for s in p.schueler:
			spass[s] = sum([p.prefbetter[s,t] for t in p.themen if self.machtthema[s,t]])
			gesamtspass += spass[s]
		topr = PrettyTable(["Teilnehmer","Spaß"])
		for s in sorted(p.schueler, key=lambda s : spass[s]):
			topr.add_row([s.cname(), "%.2f" % spass[s]])
		print topr
		
		print "Gesamter Spaß: %.2f" % gesamtspass
	
	def mache_kursplan_tex(self):
		p = self.problem
		gl = self.glob
		template = file("kursplan.tex","r").read().decode('utf8')
		stemplate = file("kursplan-zeit.tex","r").read().decode('utf8')
		eersetzen = {"themen": u""}
		for t in p.themen:
			eersetzen["themen"] += u"\\thema{%s}{%s}\n" % (tex(t.titel), tex(t.beschreibung))
		for z in p.zeiteinheiten:
			ersetzen = {"name": z.name, "kursliste": u""}
			for t in p.themen:
				if gl.raum_von[t,z]:
					ersetzen["kursliste"] += u"\\hline\n%s&%s&%s&%d\\\\\n" % (tex(t.titel), tex(gl.betreuer_von[t,z].cname()), tex(gl.raum_von[t,z].name), len(self.teilnehmer_von[t,z]))
			eersetzen["plan%d" % z.stelle] = stemplate % ersetzen
		file("kursplan-ergebnis.tex","w").write((template % eersetzen).encode('utf8'))
		subprocess.call(["latexmk","-pdf","kursplan-ergebnis.tex","-silent"])
	
	def mache_stundenplaene_tex(self):
		p = self.problem
		gl = self.glob
		schuelerplaene = u""
		with open("stundenplan.tex") as stundenplan_datei:
			template = stundenplan_datei.read().decode('utf8')
		with open("stundenplan-einzeln.tex") as stundenplan_einzeln_datei:
			stemplate = stundenplan_einzeln_datei.read().decode('utf8')
		for a in p.betreuer+p.schueler:
			ersetzen = {"name": a.cname()}
			def convert(n):
				n = n.replace("Do ", "")
				n = n.replace("Fr ", "")
				n = n.replace("Sa ", "")
				n = n.replace("So ", "")
				if n[1] == ':':
					n = "\\phantom{1}"+tex(n)
				return n
			for z in p.zeiteinheiten:
				if self.stundenplan[a,z]:
					t = self.stundenplan[a,z]
					rn = gl.raum_von[t,z].name
					beschr = "ca. %d Teilnehmer" % len(self.teilnehmer_von[t,z])
					if a in p.betreuer:
						beschr += ": " + ", ".join(s.cname() for s in self.teilnehmer_von[t,z])
					else:
						beschr += ", Betreuer: "+gl.betreuer_von[t,z].cname()
					ersetzen["kurs%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}\n\n\\beschreibung{%s}}" % (convert(z.name), tex(t.titel), tex(rn), beschr)
				else:
					ersetzen["kurs%d" % z.stelle] = "\\kasten{\\bla{%s}{frei}{}}" % convert(z.name) # TODO Pausenmusik wieder reinnehmen?
			for z in p.nichtphysikzeiteinheiten:
				if z.beschreibung != "":
					ersetzen["nichtphysik%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}\n\n\\beschreibung{%s}}" % (convert(z.name), tex(z.titel), tex(z.ort), tex(z.beschreibung))
				else:
					ersetzen["nichtphysik%d" % z.stelle] = "\\kasten{\\bla{%s}{%s}{%s}}" % (convert(z.name), tex(z.titel), tex(z.ort))
			schuelerplaene += stemplate % ersetzen
		file("stundenplan-ergebnis.tex","w").write((template % {"schueler": schuelerplaene}).encode('utf8'))
		subprocess.call(["latexmk","-pdf","stundenplan-ergebnis.tex","-silent"])
