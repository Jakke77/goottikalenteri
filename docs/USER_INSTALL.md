# Varjoaika: deb-paketti ja käyttäjäasennus

[Lataa paketti, käyttäjäasennin ja ohje ZIP-tiedostona](https://github.com/Jakke77/goottikalenteri/archive/refs/heads/apt.zip).
Pura ZIP omaan hakemistoon. Paketti sisältää kalenterin ja widgetin sekä huuhkajan huhuilua jäljittelevän ilmoitusäänen.

## Tavallinen Ubuntu-asennus

```bash
sudo apt install ./varjoaika_*.deb
```

APT asentaa PyQt6- ja Qt Multimedia -riippuvuudet. Sovellusvalikossa ovat **Varjoaika** ja **Varjoaika-widget**.
Paketin asennus ei käynnistä sovellusta rootina eikä muokkaa käyttäjän tietoja tai kirjautumisasetuksia.
Jos käytit aiemmin lähdekoodiversion käyttäjäkäynnistimiä, päivitä ne järjestelmäpakettiin tavallisena käyttäjänä:

```bash
/usr/bin/python3 /usr/share/varjoaika/install.py
```

## Asennus omalle käyttäjälle ilman root-oikeuksia

```bash
python3 install-user.py ./varjoaika_*.deb
```

Asennin purkaa sovelluksen kotihakemistoon `dpkg-deb`:llä, tarkistaa Qt-riippuvuudet ennen asennusta ja luo käyttäjän käynnistimet.
Se ei suorita paketin ylläpitoskriptejä eikä kutsu sudoa. Ubuntun tavallinen deb-asennin tarvitsee ylläpitäjän oikeudet.
Jos riippuvuudet puuttuvat, ylläpitäjä voi asentaa ne kerran:

```bash
sudo apt install python3-pyqt6 python3-pyqt6.qtmultimedia libnotify-bin
```

Myös käyttäjän Python-virtuaaliympäristö toimii ilman root-oikeuksia:

```bash
python3 -m venv ~/.local/share/varjoaika-runtime
~/.local/share/varjoaika-runtime/bin/python -m pip install 'PyQt6>=6.6,<7'
python3 install-user.py ./varjoaika_*.deb --python ~/.local/share/varjoaika-runtime/bin/python
```

Pidä valittu Python-ympäristö olemassa. Asentimen `--autostart-widget` ja `--autostart-calendar` ovat valinnaisia; molemmat voi antaa yhtä aikaa.
Aiempi kirjautumisen yhteydessä käynnistyminen säilyy päivityksessä.

## Kirjautumisen yhteydessä käynnistyminen

Avaa **Widgetin asetukset** tai **Ilmoitukset ja ääni**. Erilliset ruksit ovat:

- **Avaa widget kirjautuessa**
- **Avaa kalenteri kirjautuessa**

Molemmat voi valita. Käytetään yhtä autostart-tiedostoa ja yhtä prosessia, joten molemmat näkymät jakavat samat tiedot ja muistutukset.
Työpöytäsovellus käynnistyy käyttäjän kirjautuessa, ei ennen kirjautumista. Aiemmin käytössä ollut kirjautumiskäynnistys säilytetään päivityksessä.
Kalenterin sulkeminen jättää widgetin ja muistutukset käyntiin, jos widget on käytössä tai muistutuksia odottaa. **Lopeta** sulkee kaiken.

## Päivitys ja poisto

Lataa uusi paketti ja aja sama asennuskomento. Sulje ja avaa ohjelma päivityksen jälkeen.
Käyttäjäasennus vaihtaa `current`-linkin uuteen versioon; APT ei päivitä käyttäjän kotihakemistoon purettua versiota.
GitHubin `apt`-haara on pakettien latauskanava, ei suoraan lisättävä APT-palvelin.

```bash
python3 install-user.py --remove
# Järjestelmäpaketti:
sudo apt remove varjoaika
```

Ennen järjestelmäpaketin poistamista poista kirjautumiskäynnistyksen ruksit asetuksista.

Muistiinpanot ja muistutukset ovat `~/.local/share/Goottikalenteri/Goottikalenteri/`-hakemistossa.
Ulkoasu ja ääni ovat `~/.config/Goottikalenteri/Goottikalenteri.conf`-tiedostossa. Näitä ei korvata tai poisteta asennuksessa, päivityksessä tai poistossa.
Käyttäjäasennuksen vanhat julkaisut ja käynnistimien varmuuskopiot säilyvät palautusta varten.
