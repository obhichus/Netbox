# Dá se IP Fabric nahradit open-source nástroji?

Podklad pro rozhodnutí. Sepsáno 11. 10. 2026.

Značení:
- **[U]** = uvedl Roman,
- **[Z]** = ověřeno ve zdroji (verze a data vydání z PyPI k 11. 10. 2026),
- **[O]** = odhad nebo úsudek autora, je potřeba ověřit.

## Shrnutí v pěti větách

1. **[U]** SŽ platí za IP Fabric zhruba 100 USD za zařízení a rok, při ~10 000 zařízeních tedy **~1 mil. USD ročně** (orientačně 22–24 mil. Kč, podle kurzu).
2. Open-source stack **SuzieQ + Batfish + Netdisco + NetBox** pokryje většinu funkcí: sběr stavu sítě, historii, kontrolu záměru (intent), analýzu cest přes firewally a inventář. Všechny nástroje jsou v roce 2026 aktivně vydávané **[Z]**.
3. **Slabé místo je grafika.** Nic open-source nenabízí hotovou interaktivní mapu sítě s vyznačenou cestou paketu jako IP Fabric. Dá se to poskládat (NetBox Topology Views, Netdisco, SuzieQ GUI), ale vypadá to hůř a část je potřeba dopsat.
4. **[O]** Licence se nahrazuje lidmi: realisticky 3–5 lidí na stavbu a provoz, tj. **~6–12 mil. Kč ročně** plus jednorázově HW. Úspora je reálná, ale nižší, než říká samotná cena licence, a nese provozní riziko.
5. **Doporučení:** nevypínat IP Fabric naslepo. Udělat **pilot na 3–6 měsíců** na jedné oblasti, změřit pokrytí proti IP Fabricu a s čísly v ruce jít buď do náhrady, nebo do **hybridu** (IP Fabric jen na páteř a firewally, zbytek open-source) a do vyjednávání ceny.

## 1. Co IP Fabric vlastně dělá

IP Fabric je pět věcí v jednom balíku:

| # | Funkce | K čemu to SŽ používá |
|---|---|---|
| A | **Discovery** – sám najde zařízení přes SSH/SNMP, přihlásí se a stáhne config i stav (tabulky MAC, ARP, routing, sousedé…) | inventář, import do NetBoxu (plugin `ipfabric_netbox`) |
| B | **Snapshoty** – celá síť zamrzlá v čase, porovnání dvou snapshotů | co se změnilo od minula |
| C | **Grafika** – mapy lokalit a L2/L3 topologie, interaktivní | přehled pro lidi, kteří síť neznají |
| D | **Path lookup** – kudy jde paket z A do B, včetně firewallů, NAT a ACL | ověření komunikační matice |
| E | **Intent checks** – stovky hotových kontrol (nekonzistentní MTU, chybějící redundance, EOL verze…) | nálezy pro KyBe |

Plus: jeden dodavatel, podpora, hotové parsery pro desítky výrobců.

## 2. Open-source kandidáti

| Nástroj | Co dělá | Stav (11. 10. 2026) |
|---|---|---|
| **SuzieQ** | sběr *stavu* sítě přes SSH/API, ukládá do Parquetu (= snapshoty a historie), dotazy, `assert` kontroly, `path show`, jednoduché GUI | 0.25.0, vydáno 5. 8. 2026 **[Z]** |
| **Batfish** | analýza *konfigurací*: model sítě, traceroute a reachability přes ACL/firewally/NAT, porovnání dvou snapshotů, kontroly konzistence | pybatfish 2026.9.17, vydáno 18. 9. 2026 **[Z]**; **už běží v našem pilotu** |
| **Netdisco** | SNMP discovery, L2 topologie z LLDP/CDP, kde je která MAC/IP na portu, mapa sousedů | dlouhodobě udržovaný projekt, roky nasazený u velkých sítí (univerzity, ISP) **[O]** |
| **NetBox** | zdroj pravdy (co *má* být), inventář, kabely, IPAM, skripty komunikační matice | 4.6.10 v pilotu |
| **NetBox Topology Views** | grafická mapa z kabelů a zařízení v NetBoxu | 4.7.0, vydáno 18. 9. 2026 **[Z]**; kompatibilitu s NetBox 4.6 ověřit |
| **Nornir / Ansible** | vlastní sběr (LLDP, configy) a zápis do NetBoxu | Nornir 3.6.0, 2. 8. 2026 **[Z]** |
| **NetBox Diode + orb-agent** | oficiální cesta NetBox Labs pro automatický zápis discovery dat do NetBoxu | Diode plugin 1.18.0 **[Z]** |
| **LibreNMS / Zabbix** | monitoring (dostupnost, zátěž) s mapami | SŽ to možná už má; mimo hlavní srovnání |
| **Oxidized / RANCID** | pravidelné zálohy configů | vstup pro Batfish |

Poloviční cesta, ne open-source: **Slurp'it** (discovery napojené přímo na NetBox, plugin `slurpit_netbox` 1.4.18 **[Z]**) je komerční, ale řádově levnější cílený nástroj. Cenu ověřit u výrobce.

## 3. Srovnání funkce po funkci

Hodnocení: ● plně, ◐ částečně / s prací navíc, ○ chybí.

| Funkce IP Fabric | Open-source náhrada | Pokrytí | Poznámka |
|---|---|---|---|
| A. Discovery nových zařízení | Netdisco (SNMP, CDP/LLDP) + seed list | ◐ | IP Fabric hledá sám přes SSH; Netdisco přes SNMP. Dobré pro L2, horší pro firewally. |
| A. Sběr stavu (MAC, ARP, routy, BGP/OSPF, LLDP) | SuzieQ | ● / ◐ | Silné pro Cisco, Juniper, Arista, Cumulus/SONiC. Méně běžní výrobci (průmyslové switche) **[O]** chybí a museli by se dopsat. |
| A. Configy | Oxidized | ● | Spolehlivé, výrobcově široké. |
| B. Snapshoty a diff | SuzieQ (historie stavu) + Batfish `differentialQuestion` (configy) + Git (Oxidized) | ● | Funguje, ale ve třech nástrojích, ne v jednom okně. |
| C. Grafika lokality / L2 | NetBox Topology Views, Netdisco mapa | ◐ | Statičtější, bez živého stavu. Topology Views kreslí z kabelů v NetBoxu, takže kabely tam musí být (LLDP → NetBox skriptem). |
| C. L3 / routing mapa | – | ○ | Nic hotového. Dá se vykreslit z dat SuzieQ/Batfish (např. vlastní stránka ve D3/Cytoscape). |
| D. Path lookup se stavem (skutečné tabulky) | SuzieQ `path show` | ◐ | Bez firewallových politik a NAT. |
| D. Path lookup přes firewally, ACL, NAT | Batfish `traceroute`, `reachability`, `searchFilters` | ● / ◐ | Nejsilnější kus open-source stacku. Podpora Palo Alto, Cisco ASA/FTD, Juniper SRX dobrá; Check Point a Fortinet **[O]** částečná, nutno otestovat na našich configech. Vizualizace cesty chybí. |
| E. Intent checks | SuzieQ `assert`, Batfish otázky, NetBox Scripts (komunikační matice) | ◐ | Hotových kontrol je řádově méně; vlastní se ale píší snadno a už je píšeme. |
| Import do NetBoxu | Diode/orb-agent, vlastní skripty, Netdisco → NetBox sync | ◐ | Plugin `ipfabric_netbox` je pohodlnější; náhrada = údržba vlastního kódu. |
| Podpora, SLA | komunitní; komerčně NetBox Labs (Enterprise), jinak nic | ◐ | Pro kritickou infrastrukturu podstatné. |

**Kde je open-source dokonce lepší:**
- data zůstávají kompletně ve firmě a v otevřených formátech (Parquet, Git, PostgreSQL),
- kontroly komunikační matice přes Batfish jsou přesnější pro „co povolují pravidla“, protože pracují s celou logikou firewallu,
- žádné omezení počtem zařízení (OT, lokality, staniční sítě lze přidat bez navýšení licence).

## 4. Škálování na 10 000 zařízení

Vše níže je **[O]** odhad, pilot ho musí změřit.

- **SuzieQ:** poller lze rozdělit podle oblastí (namespace) a pustit několik pollerů paralelně. 10 000 zařízení s cyklem sběru jednou za 15–60 min je pro 2–4 VM (8–16 vCPU, 32–64 GB RAM) realistické. Úložiště desítky až stovky GB ročně podle retence.
- **Batfish:** jeden model celé sítě s 10 000 configy je velký (paměť v řádu stovek GB). Prakticky se dělí na **domény** (páteř + DC firewally, regiony), a cesty mezi doménami se skládají. Toto je technicky nejrizikovější bod.
- **Netdisco:** SNMP discovery desetitisíců zařízení zvládá; PostgreSQL + 1–2 VM.
- **NetBox:** 10 000 zařízení a stovky tisíc rozhraní jsou pro NetBox běžné; Topology Views ale u tisíců uzlů na jedné mapě zpomalí, mapy je třeba filtrovat po lokalitách.

Odhad HW: **6–10 VM**, cca 100–150 vCPU, 0,5–1 TB RAM celkem, 2–5 TB disku. Na vlastní virtualizaci SŽ jednorázově **~1–3 mil. Kč** (nebo existující kapacita).

## 5. Hrubé TCO na 3 roky

| Položka | IP Fabric | Open-source | Hybrid (IP Fabric ~2 000 zař. + OSS) |
|---|---|---|---|
| Licence | ~1 mil. USD/rok **[U]** ≈ 70 mil. Kč / 3 roky | 0 | ~0,2 mil. USD/rok **[O]** ≈ 14 mil. Kč / 3 roky |
| Lidé – stavba (rok 1) | ~0,5 FTE | 3–5 FTE | 2–3 FTE |
| Lidé – provoz (rok 2+) | ~0,5–1 FTE | 2–3 FTE | 1,5–2 FTE |
| HW | malý (appliance/VM) | 1–3 mil. Kč | 1–2 mil. Kč |
| Podpora | v ceně | volitelně NetBox Labs Enterprise | IP Fabric v ceně |
| **Celkem 3 roky [O]** | **~75 mil. Kč** | **~20–35 mil. Kč** | **~30–40 mil. Kč** |

Předpoklady **[O]**: 1 FTE síťového/automatizačního inženýra ≈ 2–2,5 mil. Kč ročně včetně odvodů; kurz ~23 Kč/USD; cena 100 USD/zař. platí i pro menší objem (nemusí – u hybridu může být jednotková cena vyšší).

Čtení: i s pesimistickým odhadem lidí vychází open-source na **zhruba třetinu až polovinu**. Jenže lidi, kteří umějí SuzieQ, Batfish a Python, se na trhu těžko shánějí, a to je reálné riziko, ne položka v tabulce.

Další páka: **při 10 000 zařízeních je 100 USD/zař. ceníková cena**. Výsledky pilotu jsou nejlepší argument pro vyjednávání slevy, i když se nakonec IP Fabric ponechá.

## 6. Rizika

| Riziko | Dopad | Jak zmírnit |
|---|---|---|
| Lidé a know-how: stack drží 1–2 lidé | po odchodu se rozpadá | min. 3 lidi, dokumentace v repu, kód v Gitu, školení |
| Podpora výrobců zařízení (průmyslové/OT switche, starší HW) | díry v datech | v pilotu změřit pokrytí po výrobcích; chybějící parsery dopsat nebo nechat na SNMP (Netdisco) |
| Batfish na celé síti | path lookup nepokryje vše | rozdělení na domény, začít páteří a firewally |
| Grafika horší než IP Fabric | menší přijetí u uživatelů a vedení | Topology Views + jedna vlastní stránka s cestou; jasně komunikovat |
| Žádné SLA | výpadek nástroje nikdo „nemusí“ opravit | provozní tým, monitoring stacku, volitelně NetBox Labs Enterprise |
| Přerušení dat při přechodu | ztráta historie | běh paralelně s IP Fabricem minimálně jeden licenční cyklus |
| Bezpečnost: sběrné účty se čtením configů | únik citlivých dat | read-only účty, trezor hesel, stack jen ve vnitřní síti (jako NetBox dnes) |

## 7. Doporučený stack

Navazuje na to, co už v repu je (NetBox 4.6.10, Batfish, skripty komunikační matice, offline balík pro RHEL9):

```
             ┌─────────────── NetBox (zdroj pravdy, co MÁ být) ───────────────┐
             │  inventář · kabely · IPAM · komunikační matice · Topology Views │
             └──────▲──────────────────▲─────────────────────▲─────────────────┘
                    │ Diode / skripty  │ LLDP → kabely        │ výsledky kontrol
   Netdisco ────────┘                  │                      │
   (SNMP discovery, L2, MAC/ARP)       │                      │
   SuzieQ ─────────────────────────────┘  stav sítě, historie, assert
   Oxidized ──► Git s configy ──► Batfish ── path lookup přes FW/NAT, diff snapshotů
```

- **NetBox** zůstává středem; IP Fabric plugin nahradí Diode + vlastní synchronizace.
- **Komunikační matice:** dnes ji kontrolujeme proti datům z IP Fabricu. V OSS variantě ji kontroluje **Batfish** (povolují pravidla?) a **SuzieQ** (existuje cesta ve skutečném stavu?). Verdikty `POVOLENO / BLOKOVÁNO / NEDOSTUPNÉ` zůstávají stejné.
- Vše jako kontejnery v **podmanu na RHEL9**, stejně jako dnešní offline balík.

## 8. Pilotní plán (3–6 měsíců)

Cíl: změřit, kolik z IP Fabricu umíme nahradit, na reálných datech SŽ, **zatímco IP Fabric dál běží**.

**Fáze 0 – rozsah (2 týdny)**
- Vybrat oblast: jedna regionální síť + jeden datacentrový firewall cluster, cca 300–800 zařízení.
- Seznam výrobců a modelů v oblasti (z IP Fabricu se dá vyexportovat).
- Read-only sběrný účet, souhlas bezpečnosti.

**Fáze 1 – sběr (4–6 týdnů)**
- Oxidized na configy, SuzieQ poller, Netdisco.
- Metrika: **% zařízení s úspěšným sběrem** proti inventáři IP Fabricu, rozpad podle výrobce.

**Fáze 2 – NetBox a grafika (3–4 týdny)**
- LLDP → kabely v NetBoxu, Topology Views pro vybrané lokality.
- Metrika: shoda kabelů/sousedů s IP Fabricem (%), názor 3–5 uživatelů na mapy.

**Fáze 3 – path lookup a komunikační matice (4–6 týdnů)**
- Batfish nad configy oblasti, kontrola komunikační matice přes Batfish i přes IP Fabric.
- Metrika: **shoda verdiktů** na stejné matici (cíl > 95 %), rozbor rozdílů.

**Fáze 4 – vyhodnocení (2 týdny)**
- Pokrytí, náročnost provozu (hodiny týdně), HW, chybějící funkce.
- Rozhodnutí: plná náhrada / hybrid / ponechat IP Fabric a vyjednat cenu.

**Co pilot potřebuje:** 2–3 lidi na část úvazku, 3–4 VM ve vnitřní síti, read-only přístup na zařízení v oblasti, přístup do API firemního IP Fabricu pro porovnání.

## 9. Co je potřeba ověřit dřív, než se rozhodne

- Skutečná smluvní cena a výpovědní lhůta IP Fabricu (100 USD/zař. je údaj od Romana).
- Rozložení výrobců v síti SŽ, hlavně firewally a OT/průmyslové switche.
- Kolik lidí je SŽ ochotna na stack dlouhodobě vyčlenit.
- Kompatibilita NetBox Topology Views 4.7 s NetBox 4.6 (případně upgrade NetBoxu).

## Zdroje

- SuzieQ – https://github.com/netenglabs/suzieq, https://pypi.org/project/suzieq/
- Batfish – https://github.com/batfish/batfish, https://pypi.org/project/pybatfish/
- Netdisco – https://github.com/netdisco/netdisco
- NetBox Topology Views – https://github.com/netbox-community/netbox-topology-views
- Nornir – https://pypi.org/project/nornir/
- NetBox Diode – https://github.com/netboxlabs/diode
- Slurp'it NetBox plugin – https://pypi.org/project/slurpit_netbox/
- Oxidized – https://github.com/ytti/oxidized
