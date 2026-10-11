# O projektu: NetBox + IP Fabric + komunikační matice (pilot pro SŽ / KyBe)

Zdroj: pracovní session s Claude 4.–18. 9. 2026 (stavba stacku, skripty, dokumenty, prezentace pro vedení)
a prezentace „Komunikační matice v NetBoxu“ z 6. 10. 2026. Sepsáno 11. 10. 2026 při přenosu do repozitáře.
Značení:
- **[U]** = uvedeno uživatelem (citace nebo parafráze jeho zprávy)
- **[P]** = zapsáno v paměťové poznámce session (2026-09-06), formulováno asistentem z toho, co řekl uživatel
- **[O]** = odvozeno, tj. můj závěr. Uživatel to výslovně neřekl.

Hesla, tokeny, přihlašovací e-maily a interní IP adresy firmy jsou vynechány záměrně.

---

## 1. Co je to za projekt

- Na pracovním PC běží pilotní stack. Tvoří ho **NetBox 4.6.10** v podobě oficiálního `netbox-docker` 5.0.2, pluginy `ipfabric_netbox` 6.1.0 a `netbox_branching` 1.1.3 a vedle nich **Batfish**.
- Data ze sítě se berou z **IP Fabric**. Pilot používá veřejné **guided demo** výrobce (EU, verze 7.9.4) v režimu *remote*. Plugin proto jede s extra `ipfabric_7_9`.
- Nad daty v NetBoxu běží **NetBox Scripts** pro kontrolu **komunikační matice** (v1 a v2) a skript pro přehled firewallových pravidel.
- Výstupy:
  - runbook pro ukázku kolegům
  - provozní dokument
  - prezentace pro nové vedení SŽ (`netbox-sz-vedeni.pptx`)
  - podklady ke screenshotům pro šéfa
- **[P]** Cíl: *„demonstrace pro KyBe"*. Z IP Fabricu se naimportují data a pravidla firewallů, navrhnou se změny pravidel a odhalí se porušení komunikační matice.

## 2. Kdo je uživatel (Roman) a jeho role

- **[U]** Pracuje ve **Správě železnic (SŽ)**. Jeho účet v IP Fabricu je na firemní doméně SŽ (e-mail neuvádím).
- **[U]** Firma má **vlastní instanci IP Fabric**. **[P]** Jde o verzi **7.5**.
  - 2026-09-04 20:47 napsal: „potrebuji pripojit plugin na ip-fabric".
  - Na dotaz na verzi odpověděl „ipfabric_7_5".
- **[U]** Má **šéfa** a **kolegy**:
  - 2026-09-06: chce „zitra v praci ukazat kolegum k cemu je to dobre, analyza pravidel atd."
  - 2026-09-16: „Mam tu dotaz od sefa".
- **[P]** Stack běží na **sdíleném pracovním PC**. Šéf tam má svá data (nasazení MISP), takže se nesmí mazat nic, co není Romanovo.
- **[U]** Cílovým publikem prezentace je **nové vedení SŽ**. Zpráva z 2026-09-15 23:17 (citace):
  > „nyni je potreba vytvorit prezentaci novemu vedeni SZ, jde o to, ze dosly penize na projekty a opensource ma zelenou, data v netboxu jsou citliva a proto je dobre je mit chranene ve firme / nicmene nic jako tabulku pravdu doposavad nemame, mame ve firme ipfabric a ten by se potom pripojil ale je nutno ukazat novemu vedeni, co netbox umi a jaky to bude prinos pro KyBe a hlavne zdarma …"
- **KyBe** (kybernetická bezpečnost) je útvar nebo agenda, pro kterou má NetBox přinést užitek. **[U]** Zkratku používá uživatel sám.
  - **[O]** Je pravděpodobné, že Roman pracuje v síťovém nebo bezpečnostním týmu, který s KyBe spolupracuje. Přesný název týmu ani pozice v přepisu nezazněl.
- **NIS2 a zákon o kybernetické bezpečnosti:** **uživatel je nezmínil.** Do prezentace je doplnil asistent jako argument (slajd 4 „Co po nás chce regulace — NIS2 a kybernetická bezpečnost").
  - V poznámkách pro řečníka stojí, že konkrétní paragrafy si má Roman ověřit u bezpečnosti.
  - **[O]** Povinnosti podle NIS2 a zákona o kybernetické bezpečnosti jsou tedy předpoklad asistenta, ne tvrzení uživatele.

## 3. Proč to dělá právě on

- **[O]** Iniciativa vychází od Romana:
  - sám staví stack
  - sám připravuje ukázku pro kolegy
  - sám píše podklady pro vedení
  - šéf si od něj vyžádal screenshoty
- **[U]** Má přístup k firemnímu IP Fabricu a zná jeho verzi.
- **[O]** Je tedy přirozeným spojením mezi daty o síti a požadavky KyBe.
- **[U]** Okno příležitosti: „dosly penize na projekty a opensource ma zelenou". Bezplatné open-source řešení je tak jediná průchozí cesta.

## 4. Co řeší (problém)

- **[U]** „nic jako tabulku pravdu doposavad nemame". Ve firmě chybí *source of truth*, tedy evidence toho, jak má síť vypadat.
- **[U]** Data o síti jsou citlivá a mají zůstat **uvnitř firmy**. Proto self-hosted NetBox, ne SaaS.
- **[U]** Chce ukázat, že přes NetBox lze najít **nefunkční služby, i když nejsou v pravidlech firewallu** (2026-09-06 19:34). Odtud verdikt „NEDOSTUPNÉ" v kontrole matice.
- **[U]** Otázka 2026-09-15 22:21: „kde vezmemem komunikacni matici ?"
  - Odpověď dostupná v podkladech: běžně ji sestavují vlastníci systémů.
  - Pro demo se odvozuje z firewallových pravidel a z ručně psaného CSV (`matice-demo.csv`, `matice-demo2.csv`).
- **[U]** Proč nejde přímo importovat soubor snímku IP Fabricu do NetBoxu. Musel to zdůvodnit v provozním dokumentu (požadavek 2026-09-15 22:55).

## 5. Cíle a další kroky

**Cíle:**
- **[U]** Krátkodobě:
  - předvést kolegům import a kontrolu komunikační matice: „predvedu import a potom komunikacni matici ?" (2026-09-06 20:17)
  - získat od vedení **zelenou**: „co presne ukazat aby to bylo stunning a omracujici a aby to bylo prijato a aby to dostalo zelenou"
- **[U]** Střednědobě: připojit **firemní IP Fabric**, „ten by se potom pripojil".
- **[U]** Vysvětlit, jak se systém udržuje, aktualizuje a zálohuje, jak k němu přistupovat a jak později analyzovat síť.
- **[U]** Doložitelnost a auditní stopa. Zvažoval delší retenci changelogu: „90 dnů … zvýšit na 180 dnu nebo i na 365" (2026-09-18).

**Plán zavedení ze slajdu 17 prezentace.** Návrh asistenta, termíny jsou odhad.
- Fáze 1 (4–6 týdnů): server ve vnitřní síti, napojení na firemní IP Fabric, první automatický import, ověření inventáře.
- Fáze 2 (6–10 týdnů): sestavení matice s vlastníky systémů, první běh kontroly, vyhodnocení nálezů s bezpečností.
- Fáze 3 (průběžně): kontrola na plán, reporty pro KyBe, rozšiřování o další segmenty.
- Co se od vedení žádá (slajd 18):
  - jeden virtuální server ve vnitřní síti se zálohováním
  - čtenářský servisní účet do IP Fabricu
  - vyčleněný čas a garant

## 6. Časová osa

| Datum (2026) | Co se dělo |
|---|---|
| 09-04 večer | Údržba PC: kernel 6.5 → 6.8, repozitář Dockeru, VirtualBox, Ubuntu Pro. Původní `/opt/fw_stack` byl nefunkční (příkazy Celery, výchozí hesla). 20:47 požadavek na plugin pro IP Fabric. Zvolen `netbox-docker` (varianta 1). Downgrade z NetBox 4.7 na 4.6.10 kvůli kompatibilitě pluginu. Pomalé LTE připojení. |
| 09-05 | Build dokončen, stack zdravý (kolem 12:53). Starý stack archivován. Řešení konektivity a obnova VPN. |
| 09-06 | 09:19 nalezeno guided demo IP Fabric 7.9.4. Průzkum API. 13:18 první kontrola matice (7 řádků), 13:33 předělána na NetBox Script, 13:53 README v2. 14:03–14:47 import přes plugin: první merge 92 zařízení a 377 IP, později 95 zařízení, 873 rozhraní, 389 IP, 51 VRF a 25 VLAN. 19:34–19:35 požadavek na demo pro kolegy „zitra v praci". 19:52 publikován runbook „Komunikační matice v NetBoxu". 20:02–20:04 přejmenování zdroje a synchronizace. |
| 09-07 | **[O]** Plánovaná ukázka kolegům v práci. Průběh v přepisu není. |
| 09-08 | Uživatel našel Jobs v menu „Operace". Běh 31: OK 18, PORUŠENÍ 9, CHYBÍ 4, NEDOSTUPNÉ 5. Vznikl skript v2 s textovým polem pro cestu, protože tlačítko Procházet ve Firefoxu (snap) přes RDP nefungovalo. |
| 09-15 | Import druhého snímku („Network Audit Evidence Q2/2026"). Zvýšen timeout RQ. Výsledek 449 zařízení (po vyčištění 365), 5 263 rozhraní, 1 998 IP. 22:21 otázka, odkud vzít matici, a vznik `matice-demo2.csv`. 22:55 požadavek na provozní dokument, 22:59 publikován („Provoz NetBoxu s IP Fabric"), k tomu textová verze. 23:17 požadavek na prezentaci pro vedení. 23:29 doručena `netbox-sz-vedeni.pptx` (18 slajdů s poznámkami pro řečníka). |
| 09-16 23:07 | Dotaz šéfa: „pár screenshotů z té aplikace nad demo daty – report importu snapshotu, mapa sítě, pohled na routing a FW pravidla". Následovaly opravy názvů a sériových čísel zařízení a doplnění primárních IP. |
| 09-17 | 10:35 „co presne do prezentace vyfotit … pry 3-6 stranek presentace je azaz". Doplněny prefixy. Vytvořena nástěnka s 8 počty: 21 lokalit, 365 zařízení, 70 typů, 4 618 rozhraní, 1 659 IP, 1 142 prefixů, 440 VLAN, 123 VRF. Kontrola matice: OK 20, PORUŠENÍ 8, CHYBÍ 2, NEDOSTUPNÉ 10. 11:28 import FW pravidel z IP Fabricu: přehled 177 prvků, 204 širokých pravidel. Přidán skript s přehledem FW a odkazy na nástěnce. |
| 09-18 07:48 | Diskuse o retenci changelogu a jobů (90 → 180/365 dní kvůli doložitelnosti). Končí pokynem „dej mi oboje na nulu", tedy neomezená retence. **[O]** Provedení není v přepisu jednoznačně potvrzeno. |

## 7. Vytvořené prezentace a dokumenty

### 7.1 Runbook „Komunikační matice v NetBoxu" (2026-09-06 19:52, HTML)

- Publikum: **[U]** kolegové v práci, ukázka plánovaná na 2026-09-07.
- Struktura:
  - *Průběh*: „Inventář, který nikdo neopisoval" (import z IP Fabricu) a „Matice jako tvrzení, které jde ověřit"
  - *Čtení výsledku*, *Co s tím dál*
  - *Bilance běhu* a *Nálezy*
  - *Čtyři verdikty*: V pořádku / Porušení matice / Chybí pravidlo / Nedostupné
  - *Na co se zeptají* (připravené odpovědi) a *Kdyby něco* (záložní postup)
- Hlavní argumenty:
  - inventář vzniká automaticky
  - matice je ověřitelné tvrzení
  - kontrola najde i rozbitou službu, o které firewall neví (verdikt NEDOSTUPNÉ)

### 7.2 Provozní dokument „Provoz NetBoxu s IP Fabric" (2026-09-15 22:59, HTML + TXT)

- Požadavek **[U]** (citace):
  > „napis dokument na obsluhu netboxu a pluginami pro import, kde zduvodni, proc nejde a nelze importovat ipfabric snapshot soubor primo do netboxu … popis prvni snapshot a … ten druhy, jak ziskat komunikacni matici … za normalnich okolnosti a jak ji ziskavame my, tedy import z firewallu"
- Kapitoly:
  - *Jak to funguje*
  - *Proč nelze importovat soubor snímku přímo*:
    - soubor není formát pro výměnu dat
    - rozbalení by bylo zpětné inženýrství bez záruky
    - stejná data jsou dostupná dokumentovaným API
    - čtení souboru není ta těžká část
  - *Dva snímky a přepínání mezi nimi*, *Offline kopie snímku*
  - *Komunikační matice*: odkud se bere normálně, odkud ji bereme pro demo, jak se čte výsledek, matice z pravidel firewallu, postup
  - *Provozní postupy*, *Známá omezení a potíže*

### 7.3 Prezentace pro vedení `netbox-sz-vedeni.pptx` (2026-09-15 23:29, 18 slajdů)

Hlavní titulek: „Evidence sítě jako doklad kybernetické bezpečnosti". Podtitulek: „NetBox — otevřený zdroj, data na našich serverech, nulové licenční náklady. Návrh pro vedení Správy železnic."

| # | Slajd | Hlavní argument |
|---|---|---|
| 1 | Titulní | viz výše |
| 2 | Tři věty na začátek | shrnutí. „Žádný z těchto bodů není o nákupu nástroje… o tom, mít data a umět je předložit." |
| 3 | Co nás dnes stojí, že evidenci nemáme | výchozí stav |
| 4 | Co po nás chce regulace (NIS2 a KB) | evidence aktiv atd. **[O]** Argument doplnil asistent. |
| 5 | Co je NetBox | Apache 2.0, bez poplatků; běží u nás; zavedený standard; otevřené API |
| 6 | IP Fabric vs NetBox | IPF „už ve firmě máme" a odpovídá na otázku „jak to je". NetBox „chceme doplnit" a odpovídá na otázku „jak to má být". „Hodnota vzniká porovnáním." |
| 7 | Co už je vyzkoušené (pilot) | postaveno na vývojovém PC s veřejnými demo daty výrobce, import bez ručního zásahu |
| 8 | Jak se to plní daty | běh na zhruba 8 000 záznamech trvá asi 25 minut, lze ho naplánovat na noc |
| 9 | Komunikační matice | „jádro přínosu pro kybernetickou bezpečnost" |
| 10 | „Neprojde" nejsou dvě slova, ale tři situace | verdikty. Rozbitou službu nenajde žádná analýza FW pravidel. |
| 11 | Co kontrola našla na demo síti | 40 řádků, jeden běh, necelá minuta. Výslovně jde o demo síť, ne SŽ. |
| 12 | Co z toho vyroste dál | výhled |
| 13 | Citlivost dat | „Kompletní popis sítě je citlivý dokument. Proto zůstane u nás." |
| 14 | Co to bude stát (poctivě) | licence 0. Provoz jednotky hodin měsíčně. Největší položkou je sestavení matice, což je práce vlastníků systémů. |
| 15 | Rizika a jak je řešíme | |
| 16 | Jak se to provozuje | údržba, denní zálohy DB a konfigurace (stovky MB), přístup přes web ve vnitřní síti s rolemi |
| 17 | Plán zavedení | fáze 1–3 (viz bod 5) |
| 18 | Rozhodnutí: o co žádáme | VM, čtenářský účet do IPF, čas a garant. „Žádné licenční náklady. Žádná data mimo firmu. První výsledky do konce druhé fáze." |

U každého slajdu jsou poznámky pro řečníka, například „Termíny jsou odhad a řekni to tak".

### 7.4 Prezentace „Komunikační matice v NetBoxu“ (2026-10-06, 10 snímků)

V repu jako [prezentace/prezentace.html](prezentace/prezentace.html) (s poznámkami řečníka) a
[prezentace/prezentace.md](prezentace/prezentace.md). Kratší verze ukázky pro kolegy: problém neověřené matice,
řetězec IP Fabric → NetBox → kontrola → verdikt, inventář z prvního demo snímku (13 lokalit, 95 zařízení),
bilance běhu (OK 18, porušení 9, chybí pravidlo 4, nedostupné 5), tři typy „neprojde“, hlavní nálezy,
noční běh jako doklad pro NIS2, časté otázky a další kroky (firemní IP Fabric 7.5, reálná matice, noční běh, Batfish).

Prezentace pro vedení (7.3) je v [prezentace-vedeni/netbox-sz-vedeni.pptx](prezentace-vedeni/netbox-sz-vedeni.pptx),
znovu vygenerovaná z původního skriptu.

### 7.5 Podklady ke screenshotům pro šéfa (2026-09-16/17)

- **[U]** Šéf chtěl screenshoty importu snímku, mapy sítě, routingu a FW pravidel. Podle zadání stačí „3-6 stránek".
- Doporučení asistenta (2026-09-17 10:36), pět snímků:
  1. vyčištěná nástěnka („inventář vznikl sám")
  2. detail zařízení s vlastními poli `ipfabric_source` a `ipfabric_ingestion` (doložitelný původ)
  3. report ingesce (řízený proces s historií)
  4. výsledek kontroly matice. Hlavní slajd.
  5. path lookup v IP Fabricu pro jeden nález („NetBox řekne, že je to špatně, IP Fabric ukáže kudy")
- Případný šestý snímek: dashboard IPF a nástěnka NetBoxu vedle sebe se stejnými čísly, jako důkaz, že data nejsou vymyšlená.
- Co nefotit: sekce s nulami, lokalitu `unknown`, chybové výpisy.

## 8. Publikum a hlavní argumenty

- **Kolegové** (09-07): praktická ukázka. Import, kontrola matice, analýza pravidel.
- **Šéf**: stručné vizuální podklady.
- **Nové vedení SŽ**: rozhodnutí o zelené. Argumenty **[U]**:
  - zdarma a open source v době, kdy „dosly penize"
  - citlivá data zůstanou ve firmě
  - chybějící source of truth
  - využití už zakoupeného IP Fabricu
  - přínos pro KyBe

  Argumenty, které doplnil asistent:
  - regulace (NIS2)
  - poctivě přiznané náklady na práci
  - fázovaný plán
  - doložitelnost a auditní stopa

## 9. Otevřené otázky a úkoly (stav na konci přepisu, 2026-09-18)

- Ověřit, že retence changelogu a jobů je opravdu nastavena na 0, a hlídat růst databáze.
- **Rotovat heslo k IP Fabricu.** Během session bylo použito v konfiguraci a v příkazech.
- Napojit **firemní IP Fabric 7.5**: extra `ipfabric_7_5`, API token s právy na snímky, servisní účet jen pro čtení.
- Nastavit plánované spouštění skriptů (import, kontrola matice). Zatím není nic.
- Archivovat a exportovat changelog kvůli doložitelnosti.
- Hosty (104) a okrajová rozhraní (120) zatím nejsou naimportované.
- Komunikační matice jako vlastní objekt v NetBoxu (nápad z 09-06), ne CSV.
- Obrácená kontrola: FW pravidla, která nemají oporu v matici.
- Porovnání stavu před změnou a po ní (pre/post-change snímky).
- `API_TOKEN_PEPPER` je stále upstream výchozí. Před produkcí změnit.
- **[O]** Výsledek prezentace vedení (zelená ano/ne) a průběh ukázky kolegům v přepisu nejsou.
- **[O]** Konkrétní povinnosti podle NIS2 a zákona o kybernetické bezpečnosti má Roman ověřit u útvaru bezpečnosti. Tak to stojí i v poznámkách prezentace.

## 10. Kde co v repu najdeš

- [README.md](../README.md): nasazení na RHEL9 offline
- [commatrix/](../commatrix/): skripty a matice
- [provoz-netboxu-s-ipfabric.html](provoz-netboxu-s-ipfabric.html), [komunikacni-matice-runbook.html](komunikacni-matice-runbook.html): dokumenty 7.1 a 7.2
- [reference/REKONSTRUKCE.md](../reference/REKONSTRUKCE.md): technický postup instalace na původním stroji
