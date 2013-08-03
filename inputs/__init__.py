#!/usr/bin/python2
# -*- coding: utf-8 -*-

import pulp
import itertools
import copy
from prettytable import PrettyTable # Das ist ein Pythonpaket

#TODO: Professorenvorträge
#TODO: Einführungsvorträge früh

def macheint(a):
	if isinstance(a, int):
		return a
	else:
		return a.id

def machetupel(a):
	if isinstance(a, (list, tuple)):
		return tuple(a)
	else:
		return tuple([a])

def lpsolver():
	if pulp.GUROBI().available():
		return pulp.GUROBI()
	elif pulp.GLPK().available():
		return pulp.GLPK()
	else:
		raise ValueError("Kein LP-Optimierer gefunden!")


class Bessere(object):
	"""Stellt eine Matrix dar, die sich sowohl mit Datenbankobjekten als auch mit deren IDs indizieren lässt"""
	def __init__(self, indizes, default):
		self.indizes = indizes
		self.matrix = {tuple(map(macheint, a)): copy.deepcopy(default) for a in itertools.product(*indizes)}
	def checkkeys(self, keys):
		for k, i in zip(keys, self.indizes):
			if k.__class__ != int and k.__class__ != i[0].__class__: # FIXME Funktioniert nur, wenn len(i) > 0 ist
				raise KeyError("Wollte Objekt vom Typ {}, bekam Objekt vom Typ {}".format(i[0].__class__, k.__class__))
	def __getitem__(self, keys):
		keys = machetupel(keys)
		self.checkkeys(keys)
		keys = tuple(map(macheint, keys))
		return self.matrix[keys]
	def __setitem__(self, keys, value):
		keys = machetupel(keys)
		self.checkkeys(keys)
		keys = tuple(map(macheint, keys))
		self.matrix[keys] = value


class PulpMatrix(Bessere):
	"""Eine Matrix bestehend aus Variablen der linearen Optimierung"""
	def __init__(self, name, indizes, *args, **kwargs):
		Bessere.__init__(self, indizes, None)
		for a in itertools.product(*indizes):
			self[a] = pulp.LpVariable(name+"_".join(map(lambda x: str(macheint(x)), a)), *args, **kwargs)
		self.name = name
	def werte(self):
		"""Gibt eine Matrix mit den optimalen Variablen-Werten zurück"""
		r = Bessere(self.indizes, None)
		for a in itertools.product(*self.indizes):
			r[a] = pulp.value(self[a])
		return r

class AbstractProblem(object):
	"""Speichert eine Instanz des Stundenplanproblems (Schüler, Themen, etc.)"""
	def __init__(self, themen, betreuer, schueler, zeiteinheiten, raeume, gebiete, kompetenzen, voraussetzungen, ausnahmen, wunschthemen, raeume_ausnahmen): #TODO: Gebiete sollten hier gar nicht auftauchen. In inputs.daten.Problem sollten die Gebietsabhängigkeiten in direkte Abhängigkeiten zwischen den Themen aufgelöst werden.
		self.themen = themen
		self.betreuer = betreuer
		self.schueler = schueler
		self.zeiteinheiten = zeiteinheiten
		self.raeume = raeume
		self.gebiete = gebiete
		self.kompetenzen = kompetenzen
		self.voraussetzungen = voraussetzungen
		self.ausnahmen = ausnahmen
		self.wunschthemen = wunschthemen
		self.raeume_ausnahmen = raeume_ausnahmen
		# Ob a zur Zeit z anwesend ist
		self.istda = Bessere((self.schueler+self.betreuer,self.zeiteinheiten), 1)
		for ausnahme in ausnahmen: # TODO: Dieses Jahr hatte ich noch manuell gecheckt, dass das funktioniert, aber allgemein muss da was schlaueres hin, was die aktuellen Anmeldungen joint
			if ausnahme.nimmt_teil.personen in self.schueler+self.betreuer:
				self.istda[ausnahme.nimmt_teil.personen_id, ausnahme.zeiteinheiten_id] = 0

		# Wie gerne a Thema t mag
		self.pref = Bessere((self.betreuer+self.schueler,self.themen), 0)
		for a in (self.betreuer+self.schueler):
			W = wunschthemen[a.id]
			for w in W:
				self.pref[a,w.themen_id] = w.gerne or 0 # FIXME das "or 0" ist sehr seltsam und sollte nicht gebraucht werden
				if w.themen_id == self.mikhail_3.id:
					self.pref[a,self.mikhail_4] = w.gerne or 0
		# Wie gerne a Thema t mag (zeitlich)
		self.pref_zeit = Bessere((self.schueler,self.themen), 0)
		for a in self.schueler:
			for t in self.themen:
				self.pref_zeit[a,t] = {-1 : 0.0001, 0 : 1., 1 : 3., 2 : 8.}[self.pref[a,t]]
		# Wie gerne a Thema t mag (normiert)
		self.pref_norm = Bessere((self.schueler,self.themen), 0)
		for a in self.schueler:
			gespref = sum([self.pref_zeit[a,t] for t in self.themen])/sum([self.istda[a,z] for z in self.zeiteinheiten])
			for t in self.themen:
				self.pref_norm[a,t] = self.pref_zeit[a,t]/gespref
		# Wie gerne a Thema t mag (so normiert, dass sich seine Präferenzen im Optimalfall zu 1 addieren)
		self.prefbetter = Bessere((self.schueler,self.themen), 0)
		for a in self.schueler:
			gesistda = sum([self.istda[a,z] for z in self.zeiteinheiten])
			gespref = sum([self.pref_norm[a,t] for t in sorted(self.themen, key = (lambda t: -self.pref_norm[a,t]))[0:gesistda]])
			for t in self.themen:
				self.prefbetter[a,t] = self.pref_norm[a,t]/gespref
		# Wie viel Zeit etwa insgesamt in Thema t verbracht wird
		self.thema_beliebtheit = Bessere((self.themen,), 0)
		for t in self.themen:
			self.thema_beliebtheit[t] = sum([self.pref_norm[a,t] for a in self.schueler])

		# Ob a Gebiet g kann
		self.kanngebiet = Bessere((self.schueler,self.gebiete), False)
		for k in self.kompetenzen:
			if k.personen in self.schueler:
				self.kanngebiet[k.personen_id, k.gebiete_id] = True

		self.durchschnittskompetenz = Bessere((self.gebiete,), 0)
		for g in self.gebiete:
			self.durchschnittskompetenz[g] = len([a for a in self.schueler if self.kanngebiet[a,g]])*1./len(self.schueler)

		# Themen, die g verwenden
		self.verwendende = Bessere((self.gebiete,), [])
		# Themen, die g beibringen
		self.beibringende = Bessere((self.gebiete,), [])
		for v in self.voraussetzungen:
			t = v.themen
			if t in self.themen:
				if v.setzt_voraus_oder_bringt_bei == 0:
					self.verwendende[v.gebiete_id] += [t]
				else:
					self.beibringende[v.gebiete_id] += [t]

		# Ob Raum r zu Zeit z verfügbar ist
		self.raumverfuegbar = Bessere((self.raeume,self.zeiteinheiten), 1)
		for ausnahme in raeume_ausnahmen:
			self.raumverfuegbar[ausnahme.raeume_id, ausnahme.zeiteinheiten_id] = 0
	
	def printinfos(self):
		print len(self.raeume), "Räume", len(self.themen), "Themen", len(self.betreuer), "Betreuer", len(self.schueler), "Schüler", len(self.gebiete), "Gebiete", len(self.zeiteinheiten), "Zeiteinheiten"
	
	def zeige_gebiet(self):
		topr = PrettyTable(["ID","Gebiet","Anteil der kompetenten Schüler"])
		for g in self.gebiete:
			topr.add_row([g.id, g.titel, "%.2f" % self.durchschnittskompetenz[g]])
		print topr
