#!/usr/bin/python
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
	def __init__(self, id, titel, beschreibung, beamer, laenge=1):
		self.id = id
		self.titel = titel
		self.beschreibung = beschreibung
		self.beamer = beamer
		self.laenge = laenge
	def gutegroesse(self):
		return 8 # TODO sinnvollere größe (z.B. abhängig davon, ob's ein Experiment ist)


class Zeiteinheiten(object):
	def __init__(self, id, stelle, name, beschreibung=None, titel=None, ort=None, exkursion=None, timestamp=None):
		self.id = id
		self.stelle = stelle
		self.name = name
		self.beschreibung = beschreibung
		self.titel = titel
		self.ort = ort
		self.exkursion = exkursion
		self.timestamp = timestamp


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

class RaumAusnahme(object):
	def __init__(self, raeume_id, zeiteinheiten_id):
		self.raeume_id = raeume_id
		self.zeiteinheiten_id = zeiteinheiten_id


def getText(node):
	for c in node.childNodes:
		if c.nodeType == c.TEXT_NODE:
			return c.data
	return ""


class Problem(AbstractProblem):
	def __init__(self, problem_id=None):
		if problem_id is None:
			problem_id = "default"
		rxml = minidom.parse("xmls/{}/räume.xml".format(problem_id))
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
		pxml = minidom.parse("xmls/{}/teilnehmer-und-betreuer.xml".format(problem_id))
		schueler = []
		betreuer = []
		organisatoren = []
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
			if "Organisator" in rollen:
				organisatoren.append(p)
		schueler.sort(key=lambda x:x.name)
		betreuer.sort(key=lambda x:x.name)
		txml = minidom.parse("xmls/{}/themenauswahl.xml".format(problem_id))
		themen = []
		tids = {}
		exkursionen = []
		exids = {}
		#TODO WAS IST DAS DENN
		for tx in txml.getElementsByTagName("node"):
			t = Themen(id=int(getText(tx.getElementsByTagName("id")[0])),
			           titel=getText(tx.getElementsByTagName("Thema")[0]),
			           beschreibung=getText(tx.getElementsByTagName("Beschreibung")[0]),
			           beamer=(getText(tx.getElementsByTagName("Beamer")[0]) == "Ja"),
			           laenge=int(getText(tx.getElementsByTagName("L-nge")[0]) or 1)
			           )
			bereich = int(getText(tx.getElementsByTagName("Bereich")[0]))
			if not bereich in [315, 13]:#TODO WAS IST DAS DENN
				themen.append(t)
				tids[t.id] = t
				rid = getText(tx.getElementsByTagName("Raum")[0]) #Spezialräume eintragen
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
		themen.sort(key=lambda x: x.titel)
		zeiteinheiten = []
		nichtphysikzeiteinheiten = []
		zids = {}
		zxml = minidom.parse("xmls/{}/zeiteinheiten.xml".format(problem_id))
		for zx in zxml.getElementsByTagName("node"):
			if getText(zx.getElementsByTagName("Physikeinheit")[0]) == "Ja":
				z = Zeiteinheiten(id=int(getText(zx.getElementsByTagName("id")[0])),
					              name=getText(zx.getElementsByTagName("Zeit")[0]),
					              stelle=None,
					              timestamp=int(getText(zx.getElementsByTagName("timestamp")[0]))
					              )
				zeiteinheiten.append(z)
				zids[z.id] = z
			else:
				z = Zeiteinheiten(id=int(getText(zx.getElementsByTagName("id")[0])),
					              name=getText(zx.getElementsByTagName("Zeit")[0]),
					              stelle=None,
					              beschreibung=getText(zx.getElementsByTagName("Beschreibung")[0]),
					              titel=getText(zx.getElementsByTagName("Titel")[0]),
					              exkursion=getText(zx.getElementsByTagName("Exkursion")[0]),
					              ort=getText(zx.getElementsByTagName("Ort")[0]),
					              timestamp=int(getText(zx.getElementsByTagName("timestamp")[0]))
					              )
				nichtphysikzeiteinheiten.append(z)
				zids[z.id] = z
				if z.exkursion not in ("Ja", "Nein", ""):
					raise ValueError(z.exkursion)
				if z.exkursion == "Ja":
					self.exkursionenzeit = z
		for zs in [zeiteinheiten, nichtphysikzeiteinheiten]:
			zs.sort(key=lambda z: z.timestamp)
			for i, z in enumerate(zs):
				def convert(r):
					from datetime import datetime, timedelta
					r = datetime.strptime(r, "%Y-%m-%d %H:%M:%S")
					r += timedelta(hours=2)  # Wegen Zeitzonenproblemen...
					return r.strftime("%a %H:%M").replace("Thu", "Do").replace("Fri", "Fr").replace("Sat", "Sa").replace("Sun", "So")
				z.name = " -- ".join([convert(r) for r in z.name.split(" bis ")])
				z.stelle = i
		kompetenzen = [] # Werden glaube ich gar nicht mehr verwendet!!!
		vxml = minidom.parse("xmls/{}/alle-voraussetzungen.xml".format(problem_id))
		voraussetzungen = []
		for v in vxml.getElementsByTagName("eck_voraussetzung"):
			a = int(getText(v.getElementsByTagName("voraussetzend")[0]))
			b = int(getText(v.getElementsByTagName("Voraussetzung")[0]))
			if a in tids and b in tids: # FIXME wieso wird das gebraucht?
				voraussetzungen.append((a,tids[b]))
		wxml = minidom.parse("xmls/{}/themenwahlen.xml".format(problem_id))
		wunschthemen = {p.id: [] for p in schueler+betreuer}
		for wx in wxml.getElementsByTagName("node"):
			pid = int(getText(wx.getElementsByTagName("Benutzer")[0]))
			if pid in pids: # FIXME wieso wird das gebraucht?
				w = int(getText(wx.getElementsByTagName("Wahl")[0]))
				if w%25 == 0:
					wunschthemen[pid].append(Wunschthemen(themen_id=int(getText(wx.getElementsByTagName("Thema")[0])),
														gerne={0: -1, 25: 0, 50: 1, 75: 2, 100: 3}[w]))
		personen_ausnahmen = []
		axml = minidom.parse("xmls/{}/verpassen.xml".format(problem_id))
		for ax in axml.getElementsByTagName("user"):
			pid = int(getText(ax.getElementsByTagName("Benutzer")[0]))
			zid = int(getText(ax.getElementsByTagName("Zeiteinheit")[0]))
			if pid in pids and zid in zids:
				personen_ausnahmen.append(Ausnahmen(nimmt_teil=NimmtTeil(pids[pid]),
										zeiteinheiten_id=zid))
		raeume_ausnahmen = []
		raum_nicht_verfuegbar_xml = minidom.parse("xmls/{}/raum-nicht-verfügbar.xml".format(problem_id))
		for rx in raum_nicht_verfuegbar_xml.getElementsByTagName("node"):
			rid = int(getText(rx.getElementsByTagName("id")[0]))
			zid = int(getText(rx.getElementsByTagName("zid")[0]))
			if rid in rids and zid in zids:
				raeume_ausnahmen.append(RaumAusnahme(raeume_id=rid, zeiteinheiten_id=zid))
		AbstractProblem.__init__(self, themen, exkursionen, betreuer, schueler, zeiteinheiten, nichtphysikzeiteinheiten, raeume, kompetenzen, voraussetzungen, personen_ausnahmen, wunschthemen, raeume_ausnahmen, problem_id, organisatoren)
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
		for t in self.exkursionen: #TODO 2015 In Gänze verstehen und vielleicht eine besser Lösung finden
			if t.titel == "Astronomisch-Physikalisches Kabinett":
				assert self.exkursionenfuelle[t] <= 45
			elif t.titel == "Bergpark Wilhelmshöhe":
				assert self.exkursionenfuelle[t] <= 25
			elif t.titel == "Betriebsbesichtigung zu Volkswagen Kassel":
				assert self.exkursionenfuelle[t] <= 25
				assert self.exkursionenfuelle[t] >= 15
			elif t.titel == "Technikmuseum":
				assert self.exkursionenfuelle[t] <= 28
			else:
				assert self.exkursionenfuelle[t] <= 50 # Vernünftiger Standardwert?
		topr = PrettyTable(["Exkursion", "# Schüler"])
		for t in self.exkursionen:
			topr.add_row([t.titel, self.exkursionenfuelle[t]])
		print(topr)
		topr = PrettyTable(["Präferenz", "# Schüler mit dieser Exkursions-Präferenz"])
		for p in [-1,0,1,2,3]:
			topr.add_row([p, anzpref[p]])
		print(topr)
