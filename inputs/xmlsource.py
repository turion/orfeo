#!/usr/bin/python2
# -*- coding: utf-8 -*-

from xml.dom import minidom
from .__init__ import AbstractProblem


class Personen(object):
	def __init__(self, id, name, username):
		self.id = id
		self.name = name
		self.username = username
	def cname(self):
		return "{} ({})".format(self.name, self.username)


class Themen(object):
	def __init__(self, id, titel, beschreibung):
		self.id = id
		self.titel = titel
		self.beschreibung = beschreibung
	def gutegroesse(self):
		return 15 # TODO sinnvollere größe (z.B. abhängig davon, ob's ein Experiment ist)


class Zeiteinheiten(object):
	def __init__(self, id, stelle, name):
		self.id = id
		self.stelle = stelle
		self.name = name


class Raeume(object):
	def __init__(self, id, name, max_personen, themen_id):
		self.id = id
		self.name = name
		self.max_personen = max_personen
		self.themen_id = themen_id


class Wunschthemen(object):
	def __init__(self, themen_id, gerne):
		self.themen_id = themen_id
		self.gerne = gerne


def getText(node):
	for c in node.childNodes:
		if c.nodeType == c.TEXT_NODE:
			return c.data
	return ""


class Problem(AbstractProblem):
	def __init__(self):
		txml = minidom.parse("inputs/themenauswahl.xml")
		themen = []
		tids = []
		for tx in txml.getElementsByTagName("node"):
			t = Themen(id=int(getText(tx.getElementsByTagName("id")[0])),
			           titel=getText(tx.getElementsByTagName("Thema")[0]),
			           beschreibung="Beschreibung nicht vorhanden!")
			themen.append(t)
			tids.append(t.id)
		pxml = minidom.parse("inputs/teilnehmer_und_betreuer.xml")
		schueler = []
		betreuer = []
		pids = []
		for u in pxml.getElementsByTagName("user"):
			p = Personen(id=int(getText(u.getElementsByTagName("id")[0])),
			             name=getText(u.getElementsByTagName("Name")[0]),
			             username=getText(u.getElementsByTagName("Nick")[0]))
			pids.append(p.id)
			rollen = getText(u.getElementsByTagName("Rollen")[0])
			if "Organisator" in rollen:
				betreuer.append(p)
			else:
				schueler.append(p)
		zeiteinheiten = []
		for i, n in enumerate(["Do 16:00--17:45", "Do 18:00--19:45", "Fr 10:00--11:45", "Fr 12:00--13:45", "Sa 10:00--11:45", "Sa 12:00--13:45", "Sa 15:00--16:45", "Sa 17:00--18:45", "So 9:30--11:15", "So 11:30--13:15"]):
			zeiteinheiten.append(Zeiteinheiten(id=i,
			                                   stelle=i,
			                                   name=n))
		raeume = [] # TODO
		for i in xrange(10):
			raeume.append(Raeume(i, "Raum {}".format(i), 30, None))
		kompetenzen = [] # Werden glaube ich gar nicht mehr verwendet!!!
		vxml = minidom.parse("inputs/alle_voraussetzungen.xml")
		voraussetzungen = []
		for v in vxml.getElementsByTagName("eck_voraussetzung"):
			a = int(getText(v.getElementsByTagName("voraussetzend")[0]))
			b = int(getText(v.getElementsByTagName("Voraussetzung")[0]))
			if a in tids and b in tids: # FIXME wieso wird das gebraucht?
				voraussetzungen.append((a,b))
		personen_ausnahmen = [] # TODO
		wxml = minidom.parse("inputs/themenwahlen.xml")
		wunschthemen = {p.id: [] for p in schueler+betreuer}
		for wx in wxml.getElementsByTagName("node"):
			pid = int(getText(wx.getElementsByTagName("Benutzer")[0]))
			if pid in pids: # FIXME wieso wird das gebraucht?
				wunschthemen[pid].append(Wunschthemen(themen_id=int(getText(wx.getElementsByTagName("Thema")[0])),
				                                      gerne=int(getText(wx.getElementsByTagName("Wahl")[0]))))
		raeume_ausnahmen = [] # TODO
		AbstractProblem.__init__(self, themen, betreuer, schueler, zeiteinheiten, raeume, kompetenzen, voraussetzungen, personen_ausnahmen, wunschthemen, raeume_ausnahmen)
