# netbox-sz-vedeni.pptx: plné znění slajdů a poznámek

Rekonstruováno z finální verze `gen.js` (pptxgenjs, LAYOUT_WIDE 13,33 × 7,5 in) po obou úpravách z 2026-09-15 23:27 a 23:28. Texty jsou v pořadí, v jakém je skript přidává na slajd (tj. zhruba shora dolů, zleva doprava). Řádky tabulek jsou odděleny ` | `.

## Slajd 1

> Evidence sítě jako doklad
> kybernetické bezpečnosti

> NetBox — otevřený zdroj, data na našich serverech, nulové licenční náklady

> Návrh pro vedení Správy železnic     ·     ověřeno na pilotu

**Poznámky řečníka:**

Úvodní věta: "Nemáme dnes jedno místo, kde by bylo napsáno, co v naší síti je a co spolu smí komunikovat. Chci ukázat, že to jde mít, že to jde mít zadarmo a že data přitom neopustí barák."

Nepředstírej, že pilot běžel na naší síti — běžel na demo datech výrobce. Řekni to hned, získáš tím důvěru na celý zbytek.

## Slajd 2

> SHRNUTÍ

> Tři věty na začátek

> 1

> Dnes nemáme evidenci sítě.

> Neexistuje jedno místo, kde je zapsáno, co v síti je, komu to patří a co spolu smí komunikovat. Každý audit i každá změna proto začíná ručním zjišťováním.

> 2

> Nástroj na to máme a je zdarma.

> NetBox je otevřený software bez licenčních poplatků. IP Fabric, který ho naplní daty, už ve firmě je. Spojení obojího je práce, ne nákup.

> 3

> Výstupem je doklad, ne obrázek.

> Kontrola komunikační matice říká, co prochází, co nemá, a kdo to má řešit — s časem, jménem a historií. Přesně to, na co se ptá auditor.

**Poznámky řečníka:**

Tohle je celá prezentace ve zkratce. Kdyby tě po třech minutách přerušili a zeptali se "tak co po nás chcete", odpověz větou tři: chceme mít doklad, ne obrázek.

## Slajd 3

> VÝCHOZÍ STAV

> Co nás dnes stojí, že evidenci nemáme

> Nikdo neví, co přesně v síti je

> Inventář žije v hlavách lidí a v tabulkách, které si každý vede po svém. Při odchodu člověka odchází i znalost.

> Změna se plánuje naslepo

> Před každým zásahem se ručně zjišťuje, co je na co navázané. Trvá to dny a stejně se na něco zapomene.

> Pravidla firewallu nikdo neumí obhájit

> Pravidla přibývají, neubývají. Nikdo neví, které je ještě potřeba a které tam zbylo po projektu z roku 2019.

> Audit začíná od nuly

> Každá kontrola znamená znovu posbírat podklady. Není z čeho doložit, že něco platí, natož od kdy.

**Poznámky řečníka:**

Nemluv o nástrojích, mluv o tom, co se děje dnes. Vedení to zná z vlastní zkušenosti — každý z nich už někdy čekal na odpověď "co je na tom portu".

Kdyby padla námitka "vždyť něco máme": ano, máme dílčí evidence. Nemáme jednu, na kterou se dá odkázat.

## Slajd 4

> NIS2 A KYBERNETICKÁ BEZPEČNOST

> Co po nás chce regulace

> Evidence aktiv

> Vědět, co provozujeme. Ne seznam serverů, ale síť včetně vazeb.

> Řízení přístupu mezi segmenty

> Doložit, které komunikace jsou povolené a proč — a že se to kontroluje.

> Doložitelnost v čase

> Ukázat nejen dnešní stav, ale i že se stav kontroloval, kdy a s jakým výsledkem.

> Řízení změn

> Vědět, kdo co změnil a proti čemu se změna posuzovala.

> Žádný z těchto bodů není o nákupu nástroje. Všechny jsou o tom, mít data a umět je předložit.

**Poznámky řečníka:**

Konkrétní paragrafy nového zákona o kybernetické bezpečnosti si před jednáním ověř u bezpečnosti — nechci, aby ses chytil na číslo, které se mezitím změnilo. Mluv o povinnostech, ne o paragrafech.

## Slajd 5

> NÁSTROJ

> Co je NetBox

> Evidence sítě, kterou používá většina velkých operátorů

> Otevřený software, licence Apache 2.0 — bez poplatků, bez omezení počtu zařízení či uživatelů.
> Běží na našem serveru, v naší síti, s naší databází. Nic neodchází ven.
> Zavedený standard: dokumentace, komunita, dostupné znalosti na trhu práce.
> Otevřené rozhraní — data se dají napojit na ticketing, monitoring i automatizaci.

> Licenční náklady

> 0 Kč

> ročně, bez ohledu na velikost sítě

**Poznámky řečníka:**

Nezamlčuj, že existuje i placená verze od NetBox Labs. Řekni rovnou: komunitní vydání nám stačí, placená podpora je volba, ne podmínka. Kdo to ví od tebe, nebude to považovat za háček.

## Slajd 6

> JAK TO ZAPADÁ

> Dva nástroje, každý na jinou otázku

> IP Fabric

> už ve firmě máme

> Odpovídá na otázku „jak to je".
>
> Projde síť, načte konfigurace a stav, a umí spočítat, kudy provoz reálně teče a kde se zahodí.

> NetBox

> chceme doplnit

> Odpovídá na otázku „jak to má být".
>
> Drží schválený stav, vlastníky, komunikační matici a historii kontrol. To IP Fabric ze své podstaty neví.

> Hodnota nevzniká v žádném z nich zvlášť. Vzniká porovnáním.

**Poznámky řečníka:**

Tohle je věta, kterou si mají zapamatovat. Zopakuj ji.

Kdyby se někdo zeptal "a nestačí nám IP Fabric sám?": umí vlastní kontroly a je v tom dobrý. Neumí ale držet schválený stav v jazyce systémů a vlastníků a nedá se do něj pustit auditor ani vlastník aplikace. To je rozdíl mezi měřicím přístrojem a evidencí.

## Slajd 7

> PILOT

> Co už je vyzkoušené

> Postaveno a odladěno na vývojovém PC, s daty z veřejné demo sítě výrobce IP Fabricu. Import proběhl bez ručního zásahu.

> 365

> zařízení

> 4 618

> rozhraní

> 1 713

> IP adres

> 21

> lokalit

> Vše výše vzniklo automaticky z jednoho snímku sítě. Nikdo nic neopisoval, nic se needitovalo ručně. Stejný postup zafunguje na našem IP Fabricu — liší se jen adresa a přihlašovací údaje.

**Poznámky řečníka:**

Zdůrazni slovo AUTOMATICKY a slovo DEMO. Obojí musí zaznít v jedné větě, jinak si budou myslet, že je to naše síť.

Číslo, které zabírá nejvíc: 4 618 rozhraní. Ručně by to nikdo nikdy nesepsal.

## Slajd 8

> POSTUP

> Jak se to plní daty

> 1

> IP Fabric projde síť

> Načte konfigurace a stav ze zařízení. Tuhle část už dnes provozujeme.

> 2

> Data se přenesou do NetBoxu

> Automaticky, přes rozhraní. Bez ručního přepisování.

> 3

> Vznikne návrh změn

> Import nezapisuje rovnou. Nejdřív ukáže, co by se změnilo, a to jde schválit.

> 4

> Změny se promítnou

> Teprve po schválení. S historií, kdo a kdy.

> Celý běh na 8 000 záznamech trvá přibližně 25 minut a dá se spustit na plán, třeba každou noc.

**Poznámky řečníka:**

Krok 3 je ten, který vedení ocení nejvíc, i když to není vidět na první pohled: import nikdy nesahá do ostrých dat napřímo. Nejdřív návrh, pak schválení. Stejný princip, jaký znají z řízení změn.

## Slajd 9

> JÁDRO PŘÍNOSU PRO KYBERNETICKOU BEZPEČNOST

> Komunikační matice

> Co to je

> Seznam tvrzení o tom, co spolu smí a nesmí komunikovat. Vzniká z architektury aplikací a od vlastníků systémů — není to síťový dokument, je to rozhodnutí firmy.
>
> Dnes taková tabulka neexistuje. Její sepsání je největší kus práce celého zavedení a nenahradí ho žádný nástroj.

> Co s ní umíme

> Každý řádek matice se ověří simulací cesty v IP Fabricu a porovná se skutečností. Nic se přitom do sítě neposílá.
>
> Výstupem je seznam rozporů s časem, odpovědností a historií. Kontrola se dá pustit opakovaně a sledovat vývoj.

**Poznámky řečníka:**

Buď tady maximálně poctivý: sepsání matice je práce lidí a bude to bolet. Když to zamlčíš a vyjde to najevo za půl roku, přijdeš o kredit. Když to řekneš teď, vypadá to jako realistický plán, ne jako prodej.

## Slajd 10

> JAK SE ČTE VÝSLEDEK

> „Neprojde" nejsou dvě slova, ale tři situace

> V POŘÁDKU

> Skutečnost odpovídá matici.

> Neřeší nikdo

> PORUŠENÍ MATICE

> Zakázaná komunikace prochází.

> Řeší bezpečnost

> CHYBÍ PRAVIDLO

> Povolenou komunikaci zahodil firewall.

> Řeší správce pravidel

> NEDOSTUPNÉ

> Zahozeno bez účasti firewallu — chybí trasa.

> Řeší síťař

> Poslední kategorii nenajde žádná analýza firewallových pravidel — rozbitá služba, o které firewall vůbec neví.

**Poznámky řečníka:**

Tady zpomal. Tohle je intelektuální jádro celé prezentace a zároveň to, čím se odlišíš od běžné prezentace o nástroji.

Příklad na dokreslení: služba, která jedním směrem funguje a druhým ne, protože chybí trasa zpátky. Firewall to neukáže, protože se k němu provoz vůbec nedostane.

## Slajd 11

> UKÁZKA METODY — NE NAŠE SÍŤ

> Co kontrola našla na demo síti

> Čtyřicet řádků matice, jeden běh, necelá minuta. Nálezy níže pocházejí z veřejné demo sítě výrobce, ne ze Správy železnic.

| Nález | Zjištění | Kategorie |
| Telnet otevřený na prvcích správy | Nešifrovaná správa je průchozí, včetně firewallu | Porušení matice |
| SSH z cloudu do vnitřní sítě | Provoz projde přes tři pravidla až k cíli | Porušení matice |
| Sdílení souborů mezi pobočkami | Prochází přes páteř, matice to zakazuje | Porušení matice |
| Služba funguje jen jedním směrem | Zpět chybí trasa, firewall v tom nefiguruje | Nedostupné |
| Správa firewallu z jádra nefunguje | Zahozeno na prvním prvku, nikdo o tom neví | Nedostupné |

> Takhle vypadá výsledek na síti, kterou nikdo předtím takto nezkontroloval. Naši síť zatím nikdo nezkontroloval vůbec.

**Poznámky řečníka:**

Poslední věta je nejsilnější moment celé prezentace. Řekni ji pomalu a nech chvíli ticho.

Pokud se zeptají "a co by to našlo u nás?" — odpověz upřímně: nevím, a právě proto o to žádám. Nikdy neslibuj konkrétní počet nálezů.

## Slajd 12

> VÝHLED

> Co z toho vyroste dál

> Analýza sítě před změnou

> Co je na co navázané, koho se zásah dotkne, co se stane při výpadku prvku. Odpověď z evidence místo obvolávání.

> Návrh změn nanečisto

> Změna se dá namodelovat stranou, prohlédnout jako rozdíl a teprve pak schválit. Stejný mechanismus, jakým probíhá import.

> Pravidelná kontrola bez člověka

> Kontrola matice běží na plán. Když někdo otevře pravidlo, které tam nepatří, víme to ráno, ne u příštího auditu.

> Podklady pro audit na jedno kliknutí

> Kdy se kontrolovalo, co vyšlo, kdo to spustil. Historie je vedlejší produkt provozu, ne zvláštní úkol.

**Poznámky řečníka:**

Nezdržuj se tu dlouho. Je to slide "co bude, až to poběží" — vedení potřebuje vidět, že to není jednorázový projekt, ale schopnost, která zůstane.

## Slajd 13

> CITLIVOST DAT

> Kompletní popis sítě je citlivý dokument.
> Proto zůstane u nás.

> Vlastní server ve vnitřní síti

> Žádná cloudová služba, žádný externí provozovatel, žádné odesílání dat ven.

> Vlastní databáze a zálohy

> Data i zálohy leží na našich discích, pod našimi pravidly pro uchovávání.

> Přístup jen pro určené role

> NetBox má vlastní správu oprávnění — kdo co vidí a kdo smí měnit, se nastavuje po skupinách.

> Otevřený kód znamená kontrolu

> Nikdo neposílá telemetrii, kterou bychom neviděli. Kód je veřejný a auditovatelný.

**Poznámky řečníka:**

Tenhle slide je odpověď na námitku dřív, než zazní. Kompletní mapa sítě je přesně to, co by útočník chtěl — a právě proto ji nechceme nikde venku.

Zároveň je to argument pro otevřený zdroj, ne proti němu: u uzavřeného produktu nevíš, co posílá domů.

## Slajd 14

> NÁKLADY — POCTIVĚ

> Co to bude stát

| Položka | Náklad | Poznámka |
| Licence NetBox | 0 Kč | Otevřený software, Apache 2.0 |
| IP Fabric | 0 Kč navíc | Máme, využijeme stávající licenci |
| Server | jeden virtuál | 4 jádra, 8 GB RAM, 100 GB disku |
| Zálohování | v rámci stávajícího | Databáze a konfigurace, denně |
| Provoz a aktualizace | jednotky hodin měsíčně | Aktualizace dvakrát až čtyřikrát ročně |
| Sestavení matice | největší položka | Práce vlastníků systémů, ne nástroje |

> Neskrývám poslední řádek. Nástroj je zdarma, práce není — a je to práce, kterou kvůli regulaci odvedeme i tak.

**Poznámky řečníka:**

Poslední řádek je záměrně v tabulce. Kdybys ho vynechal a někdo se zeptá, vypadá to, že jsi to schoval. Takhle vypadáš jako člověk, který ví, do čeho jde.

Čísla u serveru si před jednáním ověř podle toho, co je zvykem u nás — ať nesedí vedle člověka z provozu a nekroutí hlavou.

## Slajd 15

> CO MŮŽE NEVYJÍT

> Rizika a jak je řešíme

> „Otevřený software nemá podporu."

> Komunitní vydání má dokumentaci i širokou komunitu. Placená podpora od výrobce existuje a dá se dokoupit, když ji budeme chtít — není podmínkou provozu.

> „Bude na tom viset jeden člověk."

> Postup je zdokumentovaný, instalace je standardní kontejnerová a znalost NetBoxu je běžně dostupná na trhu. Dokumentace vzniká průběžně, ne až na konci.

> „Data budou zastaralá."

> Import běží automaticky na plán z IP Fabricu. Zastarat může jen to, co plníme ručně — a to je právě matice, kde se počítá s pravidelnou revizí.

> „Nikdo to nebude používat."

> Proto začínáme kontrolou matice, ne budováním evidence pro evidenci. První výstup je seznam konkrétních nálezů, ne prázdná databáze.

**Poznámky řečníka:**

Vytáhni námitky sám dřív, než je vytáhnou oni. Kdo si připraví protiargumenty, působí připraveně; kdo se nechá zaskočit, působí nadšeně.

## Slajd 16

> ÚDRŽBA, ZÁLOHY, PŘÍSTUP

> Jak se to provozuje

> Aktualizace

> Nová verze NetBoxu vychází přibližně čtvrtletně. Aktualizace je výměna kontejneru a migrace databáze, řádově desítky minut, s možností vrátit se zpět.
>
> Nemusí se aktualizovat každá verze — držíme se stabilní řady.

> Zálohy

> Zálohuje se databáze a konfigurace. Obojí je malé, řádově stovky megabajtů, a zapadne do stávajícího zálohovacího režimu.
>
> Obnova je nasazení zálohy do čistého kontejneru, vyzkoušené.

> Přístup

> Přes webové rozhraní ve vnitřní síti, s přihlášením. Oprávnění se řídí po skupinách a dají se navázat na doménové účty.
>
> Čtenářský přístup pro audit či vlastníky aplikací je bez rizika.

**Poznámky řečníka:**

Tenhle slide je pro provozní lidi v místnosti. Vedení ho přejde, ale kdyby chyběl, provozní by námitku vznesl a rozhodnutí by se odložilo.

## Slajd 17

> CO A KDY

> Plán zavedení

> Fáze 1

> 4–6 týdnů

> Server a první data

> Instalace ve vnitřní síti, napojení na firemní IP Fabric, první automatický import, ověření inventáře proti skutečnosti.

> Fáze 2

> 6–10 týdnů

> Matice a první kontrola

> Sestavení komunikační matice s vlastníky systémů, první běh kontroly, vyhodnocení nálezů s bezpečností.

> Fáze 3

> průběžně

> Pravidelný provoz

> Kontrola na plán, reporty pro kybernetickou bezpečnost, postupné rozšiřování o další segmenty a zdroje dat.

> První hmatatelný výstup — seznam nálezů z naší vlastní sítě — je na konci fáze 2.

**Poznámky řečníka:**

Termíny jsou odhad a řekni to tak. Fáze 2 závisí na tom, jak rychle se podaří dostat dohromady vlastníky systémů — to není v tvých rukou a je poctivé to přiznat.

## Slajd 18

> ROZHODNUTÍ

> O co žádáme

> 1

> Jeden virtuální server

> ve vnitřní síti, zařazený do stávajícího zálohování

> 2

> Čtenářský přístup k IP Fabricu

> servisní účet s právem číst data přes rozhraní

> 3

> Vyčleněný čas a garanta

> část úvazku na zavedení a odpovědnou osobu z bezpečnosti

> Žádné licenční náklady. Žádná data mimo firmu. První výsledky do konce druhé fáze.

**Poznámky řečníka:**

Skonči tímhle slidem a nech ho na plátně během diskuse. Tři konkrétní věci, nic vágního.

Kdyby došlo na "kolik to bude stát celkem" — vrať se na slide s náklady a zopakuj, že největší položka je práce, kterou kvůli regulaci odvedeme tak jako tak.
