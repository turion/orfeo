#!/usr/bin/python2
# -*- coding: utf-8 -*-

from xml.dom import minidom
from prettytable import PrettyTable # Das ist ein Pythonpaket
from .__init__ import AbstractProblem, Bessere


class Personen(object):
	def __init__(self, id, name, username, gastbetreuer):
		self.id = id
		self.name = name
		self.username = username
		self.gastbetreuer = gastbetreuer
	def cname(self):
		return self.name


class Themen(object):
	def __init__(self, id, titel, beschreibung, beamer):
		self.id = id
		self.titel = titel
		self.beschreibung = beschreibung
		self.beamer = beamer
	def gutegroesse(self):
		return 8 # TODO sinnvollere größe (z.B. abhängig davon, ob's ein Experiment ist)


class Zeiteinheiten(object):
	def __init__(self, id, stelle, name, beschreibung=None, titel=None, ort=None):
		self.id = id
		self.stelle = stelle
		self.name = name
		self.beschreibung = beschreibung
		self.titel = titel
		self.ort = ort


class Raeume(object):
	def __init__(self, id, name, max_personen, themen_id, beamer):
		self.id = id
		self.name = name
		self.max_personen = max_personen
		self.themen_id = themen_id
		self.beamer = beamer


class Wunschthemen(object):
	def __init__(self, themen_id, gerne):
		self.themen_id = themen_id
		self.gerne = gerne


class NimmtTeil(object):
	def __init__(self, personen):
		self.personen = personen
		self.personen_id = personen.id


class Ausnahmen(object):
	def __init__(self, nimmt_teil, zeiteinheiten_id):
		self.nimmt_teil = nimmt_teil
		self.zeiteinheiten_id = zeiteinheiten_id


def getText(node):
	for c in node.childNodes:
		if c.nodeType == c.TEXT_NODE:
			return c.data
	return ""


class Problem(AbstractProblem):
	def __init__(self):
		rxml = minidom.parse("inputs/r_ume.xml")
		raeume = []
		rids = {}
		for rx in rxml.getElementsByTagName("node"):
			max_personen = getText(rx.getElementsByTagName("Raumgr-e")[0])
			if max_personen == "":
				max_personen = 30
			else:
				max_personen = int(max_personen)
			r = Raeume(id=int(getText(rx.getElementsByTagName("id")[0])),
			           name=getText(rx.getElementsByTagName("Name")[0]),
			           max_personen=max_personen,
			           themen_id=None,
			           beamer=(getText(rx.getElementsByTagName("Beamer")[0]) == "Ja"))
			raeume.append(r)
			rids[r.id] = r
		raeume.sort(key=lambda x:r.name)
		pxml = minidom.parse("inputs/teilnehmer_und_betreuer.xml")
		schueler = []
		betreuer = []
		pids = {}
		for u in pxml.getElementsByTagName("user"):
			rollen = getText(u.getElementsByTagName("Rollen")[0])
			p = Personen(id=int(getText(u.getElementsByTagName("id")[0])),
			             name=getText(u.getElementsByTagName("Name")[0]),
			             username=getText(u.getElementsByTagName("Nick")[0]),
			             gastbetreuer=("Gastbetreuer" in rollen))
			pids[p.id] = p
			if "Betreuer" in rollen or "Gastbetreuer" in rollen:
				betreuer.append(p)
			else:
				schueler.append(p)
		schueler.sort(key=lambda x:x.name)
		betreuer.sort(key=lambda x:x.name)
		txml = minidom.parse("inputs/themenauswahl.xml")
		themen = []
		tids = {}
		exkursionen = []
		exids = {}
		for tx in txml.getElementsByTagName("node"):
			t = Themen(id=int(getText(tx.getElementsByTagName("id")[0])),
			           titel=getText(tx.getElementsByTagName("Thema")[0]),
			           beschreibung=getText(tx.getElementsByTagName("Beschreibung")[0]),
			           beamer=(getText(tx.getElementsByTagName("Beamer")[0]) == "Ja"))
			t.titel = t.titel.replace(u"lüs", u"lüs")
			bereich = int(getText(tx.getElementsByTagName("Bereich")[0]))
			if not bereich in [315, 13]:
				themen.append(t)
				tids[t.id] = t
				rid = getText(tx.getElementsByTagName("Raum")[0])
				if rid != '':
					rid = int(rid)
					if rid in rids:
						r = rids[rid]
						if r.themen_id is not None:
							raise Exception("Mehrere Themen teilen sich einen Spezialraum")
						r.themen_id = t.id
			elif bereich == 315:
				exkursionen.append(t)
				exids[t.id] = t
		# Mikhail hardgecodet
		self.mikhail = [p for p in betreuer if p.id == 442][0]
		self.mikhail_1 = [t for t in themen if t.id == 304][0]
		self.mikhail_2 = [t for t in themen if t.id == 305][0]
		self.mikhail_3 = [t for t in themen if t.id == 306][0]
		self.mikhail_4 = Themen(id=self.mikhail_3.id + 100000,
		                        titel=self.mikhail_3.titel + " (sequel)",
		                        beschreibung=self.mikhail_3.beschreibung,
		                        beamer=self.mikhail_3.beamer)
		themen.append(self.mikhail_4)
		themen.sort(key=lambda x: x.titel)
		zeiteinheiten = []
		nichtphysikzeiteinheiten = []
		zids = {}
		zxml = minidom.parse("inputs/zeiteinheiten.xml")
		for zx in zxml.getElementsByTagName("node"):
			if getText(zx.getElementsByTagName("Physikeinheit")[0]) == "Ja":
				z = Zeiteinheiten(id=int(getText(zx.getElementsByTagName("id")[0])),
					              name=getText(zx.getElementsByTagName("Zeit")[0]),
					              stelle=None)
				zeiteinheiten.append(z)
				zids[z.id] = z
			else:
				z = Zeiteinheiten(id=int(getText(zx.getElementsByTagName("id")[0])),
					              name=getText(zx.getElementsByTagName("Zeit")[0]),
					              stelle=None,
					              beschreibung=getText(zx.getElementsByTagName("Beschreibung")[0]),
					              titel=getText(zx.getElementsByTagName("Titel")[0]),
					              ort=getText(zx.getElementsByTagName("Ort")[0]))
				nichtphysikzeiteinheiten.append(z)
				zids[z.id] = z
				if z.titel == "Exkursionen":
					self.exkursionenzeit = z
		for zs in [zeiteinheiten, nichtphysikzeiteinheiten]:
			zs.sort(key=lambda z: z.name)
			for i, z in enumerate(zs):
				def convert(r):
					from datetime import datetime, timedelta
					r = datetime.strptime(r, "%Y-%m-%d %H:%M:%S")
					r += timedelta(hours=2)  # Wegen Zeitzonenproblemen...
					return r.strftime("%a %H:%M").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
				z.name = " -- ".join([convert(r) for r in z.name.split(" bis ")])
				z.stelle = i
		kompetenzen = [] # Werden glaube ich gar nicht mehr verwendet!!!
		vxml = minidom.parse("inputs/alle_voraussetzungen.xml")
		voraussetzungen = []
		for v in vxml.getElementsByTagName("eck_voraussetzung"):
			a = int(getText(v.getElementsByTagName("voraussetzend")[0]))
			b = int(getText(v.getElementsByTagName("Voraussetzung")[0]))
			if a in tids and b in tids: # FIXME wieso wird das gebraucht?
				voraussetzungen.append((a,tids[b]))
		wxml = minidom.parse("inputs/themenwahlen.xml")
		wunschthemen = {p.id: [] for p in schueler+betreuer}
		for wx in wxml.getElementsByTagName("node"):
			pid = int(getText(wx.getElementsByTagName("Benutzer")[0]))
			if pid in pids: # FIXME wieso wird das gebraucht?
				w = int(getText(wx.getElementsByTagName("Wahl")[0]))
				if w%25 == 0:
					wunschthemen[pid].append(Wunschthemen(themen_id=int(getText(wx.getElementsByTagName("Thema")[0])),
														gerne={0: -1, 25: 0, 50: 1, 75: 2, 100: 3}[w]))
		personen_ausnahmen = []
		axml = minidom.parse("inputs/verpassen.xml")
		for ax in axml.getElementsByTagName("user"):
			pid = int(getText(ax.getElementsByTagName("Benutzer")[0]))
			zid = int(getText(ax.getElementsByTagName("Zeiteinheit")[0]))
			if pid in pids and zid in zids:
				personen_ausnahmen.append(Ausnahmen(nimmt_teil=NimmtTeil(pids[pid]),
										zeiteinheiten_id=zid))
		raeume_ausnahmen = [] # TODO (nicht 2013)
		self.allezeiteinheiten = zeiteinheiten+nichtphysikzeiteinheiten
		self.exkursionen = exkursionen
		self.allethemen = themen+exkursionen
		AbstractProblem.__init__(self, themen, betreuer, schueler, zeiteinheiten, nichtphysikzeiteinheiten, raeume, kompetenzen, voraussetzungen, personen_ausnahmen, wunschthemen, raeume_ausnahmen)
		self.macheexkursionen()
		
	def macheexkursionen(self):
		import random
		random.seed(43)
		# Exkursionen zuordnen
		self.exkursionenfuelle = Bessere((self.exkursionen,), 0)
		self.exkursionenzuordnung = Bessere((self.schueler,), None)
		anzpref = {-1: 0, 0: 0, 1: 0, 2: 0, 3: 0}
		for s in self.schueler:
			if self.istda[s,self.exkursionenzeit]:
				tl = sorted(self.exkursionen, key=lambda t: -self.pref[s,t])
				b = 0
				while b < len(tl) and self.pref[s,tl[b]] == self.pref[s,tl[0]]:
					b += 1
				t = random.choice(tl[0:b])
				assert self.pref[s,tl[0]] == self.pref[s,t]
				anzpref[self.pref[s,t]] += 1
				self.exkursionenfuelle[t] += 1
				self.exkursionenzuordnung[s] = t
		for t in self.exkursionen:
			if t.titel == u"Astronomisch-Physikalisches Kabinett":
				assert self.exkursionenfuelle[t] <= 45
			elif t.titel == u"Bergpark Wilhelmshöhe":
				assert self.exkursionenfuelle[t] <= 25
			elif t.titel == u"Betriebsbesichtigung zu Volkswagen Kassel":
				assert self.exkursionenfuelle[t] <= 25
				assert self.exkursionenfuelle[t] >= 15
			elif t.titel == u"Technikmuseum":
				assert self.exkursionenfuelle[t] <= 28
			else:
				assert False
		topr = PrettyTable(["Exkursion", "# Schüler"])
		for t in self.exkursionen:
			topr.add_row([t.titel, self.exkursionenfuelle[t]])
		print topr
		topr = PrettyTable(["Präferenz", "# Schüler mit dieser Exkursions-Präferenz"])
		for p in [-1,0,1,2,3]:
			topr.add_row([p, anzpref[p]])
		print topr
