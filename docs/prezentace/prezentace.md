# Komunikační matice v NetBoxu

Prezentace (10 snímků). Zdroj: Slides artefakt z claude.ai, 6. 10. 2026. Otevřete `prezentace.html` v prohlížeči; poznámky řečníka jsou pod každým snímkem.


## 1. Komunikační matice v NetBoxu

- KyBe · ukázka
- Komunikační matice v NetBoxu
- Automatická kontrola firewallových pravidel proti skutečnému stavu sítě
- NetBox 4.6.10 · IP Fabric 7.9.4 (demo snímek) · 36 řádků matice · běh 24 s

> Poznámky řečníka: Dvacet minut o tom, proč se vyplatí mít inventář sítě, který se plní sám, a co se z něj dá zjistit o firewallových pravidlech.


## 2. Komunikační matice je tvrzení, které nikdo neověřuje

- Výchozí stav
- Komunikační matice je tvrzení, které nikdo neověřuje
- Matice
- žije jako tabulka v Excelu: kdo s kým smí komunikovat a na jakých portech
- Pravidla
- žijí v konfiguracích firewallů, routerů a cloudových ACL
- Mezera
- nikdo je pravidelně neporovnává, rozdíly najde až audit

> Poznámky řečníka: Komunikační matice bývá tabulka v Excelu, kterou nikdo neověřuje. Tady je z ní vstup pro kontrolu: každý řádek se v modelu sítě odsimuluje a porovná s tím, co má platit.


## 3. Co je, proti tomu, co má být

- Jak to funguje
- Co je, proti tomu, co má být
- IP Fabric
- objeví síť a drží její skutečný stav: zařízení, cesty, ACL, NAT
- NetBox
- drží zamýšlený stav: inventář, vlastníky a komunikační matici
- Kontrola
- každý řádek matice se odsimuluje v modelu sítě
- Verdikt
- CSV výstup a historie běhů přímo v NetBoxu
- Data tečou jedním směrem. Žádný testovací provoz se do sítě neposílá.

> Poznámky řečníka: Inventář nikdo neplnil ručně. Přišel ze snímku sítě a u každého objektu je vidět, ze kterého. Když se síť změní, import se spustí znovu a NetBox se dorovná. Kontrola je simulace nad modelem sítě, takže je bezpečná a dá se pustit i tam, kam bys testovací pakety neposlal.


## 4. Inventář, který nikdo neopisoval

- Krok 1 · Inventář
- Inventář, který nikdo neopisoval
- 13
- lokalit
- 95
- zařízení
- 873
- rozhraní
- 389
- IP adres
- 25
- VLAN
- 51
- VRF

> Poznámky řečníka: Organization → Sites, pak Devices → Devices. Otevři jedno zařízení a ukaž vlastní pole ipfabric_source a ipfabric_ingestion. Tohle nikdo neplnil ručně, přišlo to ze snímku sítě a u každého objektu je vidět, ze kterého.


## 5. 36 řádků matice proti snímku sítě, 24 sekund

- Krok 2 · Běh kontroly
- 36 řádků matice proti snímku sítě, 24 sekund
- 18
- V pořádku
- skutečnost odpovídá matici
- 9
- Porušení matice
- zakázané prochází
- 4
- Chybí pravidlo
- povolené zahodí firewall
- 5
- Nedostupné
- chybí trasa, bez firewallu

> Poznámky řečníka: Customization → Scripts → Kontrola komunikacni matice. Nahraj matice-demo.csv, snapshot nech prázdný, Run Script. Běh trvá zhruba 25 sekund, na konci je řádek Shrnuti a stažitelný CSV výstup.


## 6. „Neprojde“ jsou tři různé problémy s různým řešitelem

- Krok 3 · Čtení výsledku
- „Neprojde“ jsou tři různé problémy s různým řešitelem
- Porušení matice
- Zakázaná komunikace prochází. Je to díra, ne porucha.
- Řeší: bezpečnost
- Chybí pravidlo
- Povolenou komunikaci zahodí firewall. Rozhodnutí, které nikdo nezapsal.
- Řeší: správce pravidel
- Nedostupné
- Zahozeno bez účasti firewallu, chybí trasa. Analýza pravidel tohle nenajde.
- Řeší: síťaři

> Poznámky řečníka: Nezajímavé je, že něco neprojde. Zajímavé je, proč to neprojde: jestli to zakázal firewall, nebo tam prostě nevede cesta a nikdo o tom neví. Kategorie Nedostupné je ta, kterou žádná analýza samotných pravidel firewallu nenajde.


## 7. Co by zajímalo auditora

- Hlavní nálezy
- Co by zajímalo auditora
- Nález
- Cesta
- Verdikt
- Telnet otevřený na 4 prvcích včetně firewallu
- management, tcp/23
- Porušení matice
- SSH z AWS do vnitřní sítě
- 4 hopy přes 3 ACL a NAT
- Porušení matice
- SSH z AWS na management prvků
- 3 hopy, tcp/22
- Porušení matice
- SSH, SMB a RDP mezi pobočkami
- tcp/22, 445, 3389
- Porušení matice
- DNS a NTP z poboček na jádro
- udp/53, 123
- Chybí pravidlo
- Asymetrie Frankfurt ↔ Londýn
- tam 7 hopů, zpět 1
- Nedostupné

> Poznámky řečníka: Zastav se u tří nálezů: telnet, SSH z cloudu dovnitř a asymetrie Londýn–Frankfurt. SSH z AWS na management je nejzávažnější, pokud by šlo o produkci. Asymetrie je typ chyby, který se z konfigurace firewallu nedá vyčíst vůbec.


## 8. Z jednorázového auditu průběžná kontrola

- Krok 4 · Co s tím dál
- Z jednorázového auditu průběžná kontrola
- Skript může běžet každou noc. Pravidlo, které v matici není, uvidíme ráno, ne u příštího auditu.
- Doklad pro NIS2:
- kdy se kontrolovalo, co vyšlo a kdo to spustil, vše v historii NetBoxu.

> Poznámky řečníka: Výstup je CSV, běh má v NetBoxu historii a skript umí běžet na plán. Tohle se dá pustit každou noc. Když někdo zítra otevře pravidlo, které v matici není, dozvíme se to ráno, ne u příštího auditu.


## 9. Na co se nejspíš zeptáte

- Časté otázky
- Na co se nejspíš zeptáte
- Je to jen simulace?
- Ano, nad modelem sítě z konfigurací. Proto je bezpečná. Nenahrazuje pentest, ale najde i to, na co by si tester nevzpomněl.
- Jsou to reálná data?
- Ne, veřejný demo snímek IP Fabricu. Na naší instanci 7.5 se změní jen adresa a přihlašovací údaje.
- Kolik práce dá matice?
- Šest sloupců v CSV, 36 řádků vzniklo za večer. Reálnou matici stejně vyžaduje NIS2.
- Navrhne i úpravu pravidel?
- Zatím ne. Teď řekne, které pravidlo chybí a kde. Návrhy změn jsou další krok, je na to připravený Batfish.

> Poznámky řečníka: Proč NetBox, když analýzu dělá IP Fabric: IP Fabric ví, jak síť vypadá teď. NetBox drží, jak má vypadat, a k tomu historii běhů, oprávnění a plánování. Kontrola je tvrzení o shodě mezi tím, co má být, a co je, potřebuješ obojí. Na čem to může spadnout: na výběru zdrojové adresy. První běh měl čtrnáct falešných nálezů kvůli management adrese firewallu, po záměně za adresu switche se to srovnalo.


## 10. Z dema do provozu

- Další kroky
- Z dema do provozu
- 01
- Napojit firemní IP Fabric 7.5 a získat oprávnění ke čtení snímků
- 02
- Sepsat reálnou komunikační matici (stejně nutná kvůli NIS2)
- 03
- Zapnout noční běh kontroly s historií výsledků
- 04
- Batfish: návrhy konkrétních změn pravidel firewallu

> Poznámky řečníka: Plugin umí data tahat sám v režimu local, ale potřebuje na straně IP Fabricu oprávnění číst seznam snímků. Na demo serveru ho nemáme, proto teď data vkládá náš skript. Na firemní instanci má smysl o oprávnění požádat; zbytek řetězce zůstane stejný.
