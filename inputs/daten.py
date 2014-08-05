#!/usr/bin/python
# -*- coding: utf-8 -*-

raise DeprecationWarning("Das wird nicht mehr verwendet!")

import sqlalchemy
from sqlalchemy import or_
import sqlalchemy.orm # ORM = Object-Relational Mapper
import sqlalchemy.orm.exc # Fehlerdefinitionen
import sqlalchemy.ext.declarative

#TODO 1: Personendatenbank so abändern, dass spam eine Spalte von der Person ist
#TODO 2: Sicherstellen, dass Vorkenntnisse usw. nicht mit denen vom letzten Jahr vermischt werden. Notfalls die alten löschen. Kompetenzen gehören zu Teilnahmen, nicht zu Personen. (Zeile 182)

import sqlite3

sqlite_engine = "sqlite:///db.sqlite3"

engine = sqlalchemy.create_engine(sqlite_engine, module=sqlite3.dbapi2)
session = sqlalchemy.orm.sessionmaker(bind=engine)() # Eine SQL-Sitzung wird gestartet. Das zusätzliche () ist notwendig, siehe SQLAlchemy-Dokumentation.

Base = sqlalchemy.ext.declarative.declarative_base()
metadata = Base.metadata
metadata.reflect(engine) # Aktualisiere die Information über alle vorhandenen Tabellen

class IDLinker(object): # wird mit foreign key obsolet, das bei der Migration zu mysql eingeführt wird
	"""Oft hat man Tabellen mit Spalten der Form blablabla_id. Dabei ist blablabla_id die id einer Zeile aus der Tabelle blablabla, ein sogenannter Verweis.
	Man muss nun, um an diese Zeile dranzukommen, erst mal eine Abfrage durchführen. Das kann man in Python zum Glück automatisieren, und zwar mit der Methode __getattr__.
	Die wird hier so angepasst, dass das Objekt, das zu einer Reihe mit einem Eintrag blablabla_id gehört, automatisch ein Attribut mit Namen blablabla hat, das logischerweise zu der Reihe aus blablabla mit der id blablabla_id gehört.
	Siehe doc.python.org für mehr technische Details.
	Da das Datenbankformat von Orpheus auf dem Prinzip mit den _id basiert, sollte jede Klasse, die zu einer Tabelle mit solchen Spalten gehört, von IDLinker abstammen."""
	def __getattr__(self, name):
		"""Falls jemand bei einem Objekt dieser Klasse nach einem Attribut fragt und es das nicht hat, wird er automatisch an diese Funktion weitergeleitet, wobei name der Name des Attributes ist, nach dem gefragt wurde."""
		try:
			if name not in alle_klassen: # Nehmen wir mal an, es gibt tatsächlich eine Tabelle dieses Namens, die wir gemapped haben
				raise AttributeError
			relevante_id = getattr(self, name + "_id") # Nehmen wir mal an, dieses Objekt hat tatsächlich einen Eintrag des Namens blablabla_id
		except AttributeError: # Falls es die Tabelle nicht gibt oder dieses Objekt keinen Eintrag blablabla_id hat, muss man damit leben, dass dieses Attribut einfach nicht existiert.
			raise AttributeError(str(type(self)) + " object has no attribute '" + name + "'")
		else: # Kein Fehler ist aufgetreten, also können wir versuchen, die entsprechende Zeile zu finden
			try:
				return session.query(alle_klassen[name]).filter_by(id=relevante_id).one() # Wir wollen genau eine Zeile als Ergebnis
			except sqlalchemy.orm.exc.NoResultFound:
				raise AttributeError("Die Tabelle " + name + " hat keinen Eintrag mit id " + str(relevante_id) + ".")
	def __setattr__(self, name, wert):
		if hasattr(type(wert), "__tablename__") and type(wert).__tablename__ == name:
			super(IDLinker, self).__setattr__(name + "_id", wert.id)
		else:
			super(IDLinker, self).__setattr__(name, wert)

def beliebige_eingabe_zu_id(eingabe):
	"""Wandelt Zeichenketten und Datenbankzeilen zu ids um"""
	if isinstance(eingabe, int):
		return eingabe
	elif isinstance(eingabe, str):
		return int(eingabe)
	else:
		try:
			return eingabe.id
		except AttributeError:
			raise ValueError("Aus Eingabe {eingabe} kann keine id gewonnen werden.".format(eingabe=eingabe))

class Voraussetzungen(IDLinker, Base):
	__tablename__ = "voraussetzungen"
	def __init__(self, thema, gebiet, setzt_voraus_oder_bringt_bei):
		"""Argumente können Tabelleneinträge oder ids sein"""
		self.themen_id = beliebige_eingabe_zu_id(thema)
		self.gebiete_id = beliebige_eingabe_zu_id(gebiet)
		self.setzt_voraus_oder_bringt_bei = setzt_voraus_oder_bringt_bei
voraussetzungen = session.query(Voraussetzungen)

setzt_voraus = voraussetzungen.filter_by(setzt_voraus_oder_bringt_bei=0)
bringt_bei = voraussetzungen.filter_by(setzt_voraus_oder_bringt_bei=1)

class SetztVoraus(Voraussetzungen):
	def __init__(self, themen_id, gebiete_id):
		Voraussetzungen.__init__(self, themen_id, gebiete_id, 0)

class BringtBei(Voraussetzungen):
	def __init__(self, themen_id, gebiete_id):
		Voraussetzungen.__init__(self, themen_id, gebiete_id, 1)

class Gebiete(Base):
	__tablename__ = "gebiete"
gebiete = session.query(Gebiete) # Weil man es so häufig benötigt

class Themen(Base):
	"""Diese Tabelle enthält auch eine Spalte aktuelle_version_id, aber keine Verweise auf andere Tabellen.
	Daher stammt sie nicht von IDLinker ab."""
	__tablename__ = "themen" # Diese Zeile ist absolut notwendig, um die Klasse Themen mit der Tabelle themen in Verbindung zu bringen!
	def __init__(self, titel, beschreibung, kommentar="", aktuelle_version=None, min_stufe=None, typ=0, regelmaessig=True):
		self.titel = titel
		self.beschreibung = beschreibung
		self.kommentar = kommentar
		if aktuelle_version != None:
			if isinstance(aktuelle_version, int):
				self.aktuelle_version_id = aktuelle_version
			else:
				self.aktuelle_version_id = aktuelle_version.id
		self.min_stufe = min_stufe
		self.typ = typ
		self.regelmaessig = regelmaessig
	def __unicode__(self):
		return "{titel} ({beschreibung}, {kommentar})".format(titel=self.titel, beschreibung=self.beschreibung[:20].strip(), kommentar=self.kommentar[:20].strip())
	def __str__(self):
		return str(self)
	@property # Auf diese Weise kann man ganz einfach einthema.aktuelle_version aufrufen
	def aktuelle_version(self): # TODO: Das funktioniert nicht in Queries. Vllt besser mit foreign keys
		try:
			if self.aktuelle_version_id == None:
				return self
			else:
				return session.query(Themen).filter_by(id=self.aktuelle_version_id).one()
		except sqlalchemy.orm.exc.NoResultFound:
			raise AttributeError("Die Tabelle themen hat keinen Eintrag mit id {id}.".format(id=self.aktuelle_version_id))
	def gutegroesse(self):
		if self.typ == 1:
			return 6
		else:
			return 15
themen = session.query(Themen) # Weil man es so häufig benötigt
mehrstuendige_themen = themen.filter(Themen.laenge!=None)

class Personen(Base):
	__tablename__ = "personen"
	def __unicode__(self):
		return """Name:                   {self.vorname} {self.nachname}
Adresse:                {self.strasse}
                        {self.plz} {self.ort}
                        {bundesland}
Telefon der Eltern:     {self.telefon}
E-Mail-Adresse:         {self.email}
Geburtsdatum:           {self.geburtstag}.{self.geburtsmonat}.{self.geburtsjahr}
Geschlecht:             {geschlecht}
Vegetarier:             {self.vegetarier}
Datenversand:           {self.datenversand}
Forenaccount:           {self.forenaccount}
Sonstiges:              {self.kommentar}""".format(self=self, geschlecht={'m': "männlich", 'w': "weiblich", '': "nicht angegeben"}[self.geschlecht], bundesland=bundesland(self.bundesland)) # Da war auch mal der Abijahrgang dabei
	def __str__(self):
		return str(self)
	@property
	def alter(self): # TESTME
		import datetime
		try:
			geburtsdatum = datetime.date(int(self.geburtsjahr), int(self.geburtsmonat), int(self.geburtstag))
		except (TypeError, ValueError): # Eins oder mehrere der Felder waren nicht richtig gesetzt (z.B. leer, None)
			return None
		heute = datetime.date.today()
		try:
			geburtstag_dieses_jahr = geburtsdatum.replace(year=heute.year)
		except ValueError: # geburtsdatum war 29. Februar in einem Schaltjahr
			geburtstag_dieses_jahr = geburtsdatum.replace(year=heute.year, day=geburtsdatum.day-1)
		if geburtstag_dieses_jahr > heute: # Wird dieses Jahr noch Geburtstag haben
			return heute.year - geburtsdatum.year - 1
		else: # Hatte dieses Jahr schon Geburtstag
			return heute.year - geburtsdatum.year
	def name(self):
		return "{} {}".format(self.vorname, self.nachname)
	def cvorname(self):
		if self.nachname != '':
			return self.vorname.strip()
		else:
			return " ".join(self.vorname.replace(","," ").split(" ")[0:-1]).replace("  "," ").strip()
	def cnachname(self):
		if self.nachname != '':
			return self.nachname.strip()
		else:
			return self.vorname.replace(","," ").split(" ")[-1].strip()
	def cname(self):
		return "{} {}".format(self.cvorname(), self.cnachname())
personen = session.query(Personen)

class LeerePerson(Personen):
	def __init__(self):
		for spalte in Personen.__table__.columns:
			setattr(self, spalte.name, "")

class Professor(Personen):
	def __init__(self, nachname, thema):
		self.thema_id = beliebige_eingabe_zu_id(thema)
		self.nachname = "Prof. Dr. " + nachname
	def registrieren(self):
		session.add(self)
		session.commit()
		eigenes_thema = Wunschthemen()
		eigenes_thema.themen_id = self.thema_id
		eigenes_thema.personen_id = self.id
		eigenes_thema.gerne = 2
		eigenes_thema.jahr = dieses_jahr
		session.add(eigenes_thema)
		for thema in themen.filter(Themen.id!=self.thema_id): # Der Professor hält nur seinen eigenen Vortrag
			anderes_thema = Wunschthemen()
			anderes_thema.themen_id = thema.id
			anderes_thema.personen_id = self.id
			anderes_thema.gerne = -1
			anderes_thema.jahr = dieses_jahr
			session.add(anderes_thema)
		session.commit()

class ThemenAusnahmen(IDLinker, Base):
	__tablename__ = "themen_ausnahmen"

class Kompetenzen(IDLinker, Base):
	__tablename__ = "kompetenzen"
	def __init__(self, person, gebiet):
		self.gebiete_id = beliebige_eingabe_zu_id(gebiet)
		self.personen = person # todo vllt: 2012 -> nimmt_teil. Kompetenzen haben zwar ein Jahr, das ist aber nicht so schön
		self.jahr = dieses_jahr
kompetenzen = session.query(Kompetenzen)

class Wunschthemen(IDLinker, Base):
	__tablename__ = "wunschthemen"
wunschthemen = session.query(Wunschthemen)

class NimmtTeil(IDLinker, Base):
	__tablename__ = "nimmt_teil"
	def __init__(self, person):
		self.jahr = dieses_jahr
		self.personen = person
	def teilnehmerbeitrag(self):
		if self.jahr != dieses_jahr:
			raise ValueError("Teilnehmerbeiträge für vergangene Jahre wurden noch nicht implementiert")
		else:
			return (self.keine_unterkunft and status.reduzierter_teilnehmerbeitrag or status.teilnehmerbeitrag) + (self.tshirt and status.tshirtpreis or 0)
nimmt_teil = session.query(NimmtTeil)

import time
dieses_jahr = time.localtime().tm_year

aktuelle_themen_und_ausnahmen = session.query(Themen, ThemenAusnahmen).filter(Themen.id==ThemenAusnahmen.themen_id).filter(Themen.id==Themen.aktuelle_version_id).filter(ThemenAusnahmen.jahr==dieses_jahr)

aktuelle_themen = themen.filter_by(regelmaessig=1) # FIXME: Absoluter Notworkaround weil ich outer joins nicht rechtzeitig zum laufen gebracht habe. Geht nur, weil noch keine unregelmäßigen Themen eingetragen wurden. Das dürfte aber spätestens mit den Experimenten der Fall werden.

def gen_aktuelle_stattfindende_themen():
	for thema in themen:
		if (thema.regelmaessig == 1 and aktuelle_themen_und_ausnahmen.filter(Themen.id==thema.id).filter(ThemenAusnahmen.findet_statt==0).count() == 0) or (thema.regelmaessig == 0 and aktuelle_themen_und_ausnahmen.filter(Themen.id==thema.id).filter(ThemenAusnahmen.findet_statt==0).count() > 0):
			yield thema

jemals_anmeldungen = session.query(NimmtTeil, Personen).filter(NimmtTeil.personen_id==Personen.id)
aktuelle_anmeldungen = jemals_anmeldungen.filter(NimmtTeil.jahr==dieses_jahr)
aktuelle_anmeldungen_kein_spam_mit_allem = aktuelle_anmeldungen.filter(NimmtTeil.spam=='n') # Nächstes Jahr mit Joi
aktuelle_betreuer = aktuelle_anmeldungen_kein_spam_mit_allem.filter(Personen.betreuer.in_(["1", 1]))
aktuelle_anmeldungen_kein_spam_mit_warteliste = aktuelle_anmeldungen_kein_spam_mit_allem.filter(Personen.betreuer=="")
aktuelle_anmeldungen_kein_spam = aktuelle_anmeldungen_kein_spam_mit_warteliste.filter(NimmtTeil.warteliste==None)
aktuelle_anmeldungen_kein_spam_unterkunft = aktuelle_anmeldungen_kein_spam.filter(or_(NimmtTeil.keine_unterkunft==None, NimmtTeil.keine_unterkunft==""))
warteliste = aktuelle_anmeldungen_kein_spam_mit_warteliste.filter(NimmtTeil.warteliste=="1")
jemals_teilnehmer = jemals_anmeldungen.filter(NimmtTeil.spam=='n').filter(Personen.betreuer=="")
#TODO In anmeldung.py sollte doch nicht alles als string gespeichert werden, das nervt sehr
#TODO Warteliste wird noch nicht richtig gespeichert

class Bereiche(Base):
	__tablename__ = "bereiche"
	@property
	def aktuelle_themen_query(self):
		return aktuelle_themen.filter_by(bereiche_id=self.id)
	def __iter__(self):
		return iter(self.aktuelle_themen_query)
bereiche = session.query(Bereiche)

class NimmtTeilZeiteinheitenAusnahmen(IDLinker, Base): # TODO: Beim Umzug das Zeiteinheiten im Namen rausnehmen
	__tablename__ = "nimmt_teil_zeiteinheiten_ausnahmen"

class Zeiteinheiten(Base):
	__tablename__ = "zeiteinheiten"
	def __init__(self, stelle, name):
		self.jahr = dieses_jahr
		self.stelle = stelle
		self.name = name
zeiteinheiten = session.query(Zeiteinheiten)

class Raeume(IDLinker, Base):
	__tablename__ = "raeume"
	def __init__(self, name, max_personen, beamer, kommentar = None):
		self.jahr = dieses_jahr
		self.name = name
		self.max_personen = max_personen
		self.beamer = beamer
		self.kommentar = kommentar
raeume = session.query(Raeume)

def ex_raum_zuordnen(experiment, name, max_personen=8, kommentar=None):
	raum = Raeume(name, max_personen, None, kommentar)
	raum.themen_id = experiment.id
	session.add(raum)
	session.commit()

class RaeumeAusnahmen(IDLinker, Base):
	__tablename__ = "raeume_ausnahmen"

# TODO brauchen wir die beiden überhaupt?
def raumausnahme(raum, zeiteinheit): 
	raum_id = beliebige_eingabe_zu_id(raum)
	zeiteinheit_id = beliebige_eingabe_zu_id(zeiteinheit)
	return session.query(RaeumeAusnahmen).filter_by(raeume_id=raum_id, zeiteinheiten_id=zeiteinheit_id).count()

def nimmtteilausnahme(nimmt_teil, zeiteinheit):
	nimmt_teil_id = beliebige_eingabe_zu_id(nimmt_teil)
	zeiteinheit_id = beliebige_eingabe_zu_id(zeiteinheit)
	return session.query(NimmtTeilZeiteinheitenAusnahmen).filter_by(nimmt_teil_id=nimmt_teil_id, zeiteinheiten_id=zeiteinheit_id).count()


class Status(Base):
	__tablename__ = "status"
	def __init__(self, name, wert):
		self.name = name
		self.wert = wert

class StatusLeser(object):
	def __init__(self, erlaubte_namen=()):
		self.query = session.query(Status)
	def __getattr__(self, name):
		try:
			return self.query.filter_by(name=name).order_by(sqlalchemy.desc(Status.id)).first().wert
		except AttributeError:
			raise AttributeError("Status {0} wurde noch nicht gesetzt.".format(name))
	def __setattr__(self, name, wert):
		if session.query(Status.name).filter_by(name=name).count():
			self.setze(name, wert)
		else:
			object.__setattr__(self, name, wert)
	def setze(self, name, wert):
		session.add(Status(name, wert))
		session.commit()
status = StatusLeser()

alle_klassen = {"personen": Personen, "voraussetzungen": Voraussetzungen, "gebiete": Gebiete, "themen": Themen, "themen_ausnahmen": ThemenAusnahmen, "kompetenzen": Kompetenzen, "wunschthemen": Wunschthemen, "nimmt_teil": NimmtTeil, "nimmt_teil_zeiteinheiten_ausnahmen": NimmtTeilZeiteinheitenAusnahmen, "zeiteinheiten": Zeiteinheiten, "raeume": Raeume}

from .__init__ import AbstractProblem
class Problem(AbstractProblem):
	"""Reine Testklasse, die dazu dient, die alten Daten aus dem Jahr 2012 zum testen zur Verfügung zu haben"""
	def __init__(self):
		jahr = 2012
		relevante_anmeldungen = jemals_anmeldungen.filter(NimmtTeil.jahr==jahr).filter(NimmtTeil.spam=='n').filter(NimmtTeil.warteliste==None)
		betreuer = [x[1] for x in relevante_anmeldungen.filter(Personen.betreuer=="1").all()]
		betreuer.sort(key = lambda a : (a.cnachname(), a.cvorname()))
		schueler = [x[1] for x in relevante_anmeldungen.filter(Personen.betreuer=='').all()]
		schueler.sort(key = lambda a : (a.cnachname(), a.cvorname()))
		zeiteinheiten_ = zeiteinheiten.filter(Zeiteinheiten.jahr==jahr).all()
		zeiteinheiten_.sort(key = lambda z: z.stelle)
		raeume_ = raeume.filter(Raeume.jahr==jahr).all()
		raeume_.sort(key = lambda r : r.name.lower())
		raeume_ausnahmen = [x[0] for x in session.query(RaeumeAusnahmen, Raeume).filter(RaeumeAusnahmen.raeume_id==Raeume.id).filter(Raeume.jahr==jahr).all()]
		themen_ = [thema for thema in themen if wunschthemen.filter_by(jahr=jahr, themen_id=thema.id).count()]
		themen_.sort(key = lambda t : t.titel.lower())

		# Direkte Themenabhängigkeiten aus Gebieten emulieren
		voraussetzungen_ = []
		for thema in themen_:
			for voraussetzend in setzt_voraus.filter_by(themen_id=thema.id):
				for voraussetzung in bringt_bei.filter_by(gebiete_id=voraussetzend.gebiete_id):
					voraussetzungen_.append((thema, voraussetzung.themen))
		## Mikhail hardgecodet
		self.mikhail = personen.filter_by(id=132).one()
		self.mikhail_1 = themen.filter_by(id=16).one()
		self.mikhail_2 = themen.filter_by(id=17).one()
		self.mikhail_3 = themen.filter_by(id=18).one()
		self.mikhail_4 = Themen(titel=self.mikhail_3.titel,
						beschreibung=self.mikhail_3.beschreibung,
						kommentar=self.mikhail_3.kommentar,
						aktuelle_version=self.mikhail_3.aktuelle_version,
						min_stufe=self.mikhail_3.min_stufe,
						typ=self.mikhail_3.typ,
						regelmaessig=self.mikhail_3.regelmaessig)
		self.mikhail_4.id = 100000 # FIXME das ist ein übler Hack
		themen_.append(self.mikhail_4)
		self.mikhail_4.titel += " (sequel)"

		AbstractProblem.__init__(self, themen_, [], betreuer, schueler, zeiteinheiten_, [], raeume_, kompetenzen.all(), voraussetzungen_, session.query(NimmtTeilZeiteinheitenAusnahmen), {a.id: wunschthemen.filter_by(personen_id=a.id, jahr=jahr).all() for a in betreuer+schueler}, raeume_ausnahmen)
