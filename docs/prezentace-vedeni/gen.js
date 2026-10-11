const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';           // 13.3 x 7.5
pres.author = 'Maier Roman';
pres.title = 'NetBox pro Spravu zeleznic';

const DARK  = '16232B';
const SLATE = '24424E';
const AMBER = 'E0A100';
const LIGHT = 'F5F7F7';
const CARD  = 'FFFFFF';
const INK   = '16232B';
const MUTED = '5D6E75';
const LINE  = 'D5DEE0';
const OK    = '2E7D5B';
const BAD   = 'B3352F';
const WARN  = '9A6100';
const ROUTE = '3E4E96';

const HEAD = 'Cambria';
const BODY = 'Calibri';

function dot(s, x, y, color) {
  s.addShape(pres.ShapeType.rect, { x, y, w: 0.13, h: 0.13, fill: { color: color || AMBER } });
}

function lightSlide(titleText, kicker) {
  const s = pres.addSlide();
  s.background = { color: LIGHT };
  if (kicker) {
    s.addText(kicker, { x: 0.6, y: 0.42, w: 9, h: 0.28, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 11, bold: true, color: AMBER, charSpacing: 2 });
  }
  s.addText(titleText, { x: 0.6, y: kicker ? 0.72 : 0.5, w: 12.1, h: 0.85, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 32, bold: true, color: INK });
  return s;
}

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: DARK };
  return s;
}

function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.04,
    fill: { color: fill || CARD }, line: { color: LINE, width: 0.75 } });
}

/* ---------------------------------------------------------------- 1 TITUL */
{
  const s = darkSlide();
  s.addShape(pres.ShapeType.rect, { x: 0.9, y: 1.55, w: 0.55, h: 0.09, fill: { color: AMBER } });
  s.addText('Evidence sítě jako doklad\nkybernetické bezpečnosti', {
    x: 0.9, y: 1.95, w: 10.2, h: 1.9, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 40, bold: true, color: 'FFFFFF', lineSpacing: 46 });
  s.addText('NetBox — otevřený zdroj, data na našich serverech, nulové licenční náklady', {
    x: 0.9, y: 4.0, w: 10.4, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 17, color: 'B9C8CD' });
  s.addText([
    { text: 'Návrh pro vedení Správy železnic', options: { bold: true, color: 'FFFFFF' } },
    { text: '     ·     ', options: { color: SLATE } },
    { text: 'ověřeno na pilotu', options: { color: '8FA4AB' } },
  ], { x: 0.9, y: 6.35, w: 11, h: 0.4, isTextBox: true, valign: 'top', margin: 0, fontFace: BODY, fontSize: 13 });
  s.addNotes('Úvodní věta: "Nemáme dnes jedno místo, kde by bylo napsáno, co v naší síti je a co spolu smí komunikovat. Chci ukázat, že to jde mít, že to jde mít zadarmo a že data přitom neopustí barák."\n\nNepředstírej, že pilot běžel na naší síti — běžel na demo datech výrobce. Řekni to hned, získáš tím důvěru na celý zbytek.');
}

/* --------------------------------------------------------- 2 TRI VETY */
{
  const s = lightSlide('Tři věty na začátek', 'SHRNUTÍ');
  const body = [
    ['Dnes nemáme evidenci sítě.',
     'Neexistuje jedno místo, kde je zapsáno, co v síti je, komu to patří a co spolu smí komunikovat. Každý audit i každá změna proto začíná ručním zjišťováním.'],
    ['Nástroj na to máme a je zdarma.',
     'NetBox je otevřený software bez licenčních poplatků. IP Fabric, který ho naplní daty, už ve firmě je. Spojení obojího je práce, ne nákup.'],
    ['Výstupem je doklad, ne obrázek.',
     'Kontrola komunikační matice říká, co prochází, co nemá, a kdo to má řešit — s časem, jménem a historií. Přesně to, na co se ptá auditor.'],
  ];
  let y = 1.95;
  body.forEach(([h, t], i) => {
    card(s, 0.6, y, 12.1, 1.35);
    s.addText(String(i + 1), { x: 0.95, y: y + 0.3, w: 0.6, h: 0.6, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 30, bold: true, color: AMBER, align: 'left' });
    s.addText(h, { x: 1.6, y: y + 0.2, w: 10.8, h: 0.38, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 17, bold: true, color: INK });
    s.addText(t, { x: 1.6, y: y + 0.6, w: 10.8, h: 0.62, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 13.5, color: MUTED });
    y += 1.55;
  });
  s.addNotes('Tohle je celá prezentace ve zkratce. Kdyby tě po třech minutách přerušili a zeptali se "tak co po nás chcete", odpověz větou tři: chceme mít doklad, ne obrázek.');
}

/* ------------------------------------------------------------ 3 PROBLEM */
{
  const s = lightSlide('Co nás dnes stojí, že evidenci nemáme', 'VÝCHOZÍ STAV');
  const items = [
    ['Nikdo neví, co přesně v síti je', 'Inventář žije v hlavách lidí a v tabulkách, které si každý vede po svém. Při odchodu člověka odchází i znalost.'],
    ['Změna se plánuje naslepo', 'Před každým zásahem se ručně zjišťuje, co je na co navázané. Trvá to dny a stejně se na něco zapomene.'],
    ['Pravidla firewallu nikdo neumí obhájit', 'Pravidla přibývají, neubývají. Nikdo neví, které je ještě potřeba a které tam zbylo po projektu z roku 2019.'],
    ['Audit začíná od nuly', 'Každá kontrola znamená znovu posbírat podklady. Není z čeho doložit, že něco platí, natož od kdy.'],
  ];
  let x = 0.6, y = 2.0;
  items.forEach((it, i) => {
    const cx = x + (i % 2) * 6.25;
    const cy = y + Math.floor(i / 2) * 2.05;
    card(s, cx, cy, 5.85, 1.75);
    dot(s, cx + 0.35, cy + 0.42);
    s.addText(it[0], { x: cx + 0.62, y: cy + 0.28, w: 4.95, h: 0.42, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15.5, bold: true, color: INK });
    s.addText(it[1], { x: cx + 0.62, y: cy + 0.74, w: 4.95, h: 0.85, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED });
  });
  s.addNotes('Nemluv o nástrojích, mluv o tom, co se děje dnes. Vedení to zná z vlastní zkušenosti — každý z nich už někdy čekal na odpověď "co je na tom portu".\n\nKdyby padla námitka "vždyť něco máme": ano, máme dílčí evidence. Nemáme jednu, na kterou se dá odkázat.');
}

/* ------------------------------------------------------------ 4 REGULACE */
{
  const s = lightSlide('Co po nás chce regulace', 'NIS2 A KYBERNETICKÁ BEZPEČNOST');
  card(s, 0.6, 1.95, 12.1, 3.5);
  const rows = [
    ['Evidence aktiv', 'Vědět, co provozujeme. Ne seznam serverů, ale síť včetně vazeb.'],
    ['Řízení přístupu mezi segmenty', 'Doložit, které komunikace jsou povolené a proč — a že se to kontroluje.'],
    ['Doložitelnost v čase', 'Ukázat nejen dnešní stav, ale i že se stav kontroloval, kdy a s jakým výsledkem.'],
    ['Řízení změn', 'Vědět, kdo co změnil a proti čemu se změna posuzovala.'],
  ];
  let y = 2.25;
  rows.forEach(([h, t]) => {
    dot(s, 1.0, y + 0.13);
    s.addText(h, { x: 1.3, y: y - 0.02, w: 3.4, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 14.5, bold: true, color: INK });
    s.addText(t, { x: 4.8, y: y - 0.07, w: 7.6, h: 0.55, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 13, color: MUTED });
    y += 0.82;
  });
  s.addText('Žádný z těchto bodů není o nákupu nástroje. Všechny jsou o tom, mít data a umět je předložit.', {
    x: 0.6, y: 5.75, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 14, italic: true, color: SLATE });
  s.addNotes('Konkrétní paragrafy nového zákona o kybernetické bezpečnosti si před jednáním ověř u bezpečnosti — nechci, aby ses chytil na číslo, které se mezitím změnilo. Mluv o povinnostech, ne o paragrafech.');
}

/* --------------------------------------------------------- 5 CO JE NETBOX */
{
  const s = lightSlide('Co je NetBox', 'NÁSTROJ');
  card(s, 0.6, 1.95, 7.5, 3.6);
  s.addText('Evidence sítě, kterou používá většina velkých operátorů', {
    x: 0.95, y: 2.2, w: 6.8, h: 0.75, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 19, bold: true, color: INK });
  s.addText([
    { text: 'Otevřený software, licence Apache 2.0 — bez poplatků, bez omezení počtu zařízení či uživatelů.', options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: 'Běží na našem serveru, v naší síti, s naší databází. Nic neodchází ven.', options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: 'Zavedený standard: dokumentace, komunita, dostupné znalosti na trhu práce.', options: { bullet: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: 'Otevřené rozhraní — data se dají napojit na ticketing, monitoring i automatizaci.', options: { bullet: true } },
  ], { x: 0.95, y: 2.9, w: 6.85, h: 2.5, isTextBox: true, valign: 'top', margin: 0,
       fontFace: BODY, fontSize: 13.5, color: MUTED });

  card(s, 8.45, 1.95, 4.25, 3.6, DARK);
  s.addText('Licenční náklady', { x: 8.8, y: 2.3, w: 3.6, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13, color: '9FB3B9' });
  s.addText('0 Kč', { x: 8.8, y: 2.95, w: 3.6, h: 1.1, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 54, bold: true, color: AMBER });
  s.addText('ročně, bez ohledu na velikost sítě', { x: 8.8, y: 4.15, w: 3.6, h: 0.9, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 12.5, color: 'B9C8CD' });
  s.addNotes('Nezamlčuj, že existuje i placená verze od NetBox Labs. Řekni rovnou: komunitní vydání nám stačí, placená podpora je volba, ne podmínka. Kdo to ví od tebe, nebude to považovat za háček.');
}

/* ------------------------------------------- 6 SKUTECNOST vs ZAMER */
{
  const s = lightSlide('Dva nástroje, každý na jinou otázku', 'JAK TO ZAPADÁ');
  card(s, 0.6, 1.95, 5.85, 3.15);
  s.addText('IP Fabric', { x: 0.95, y: 2.2, w: 5.1, h: 0.45, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 22, bold: true, color: SLATE });
  s.addText('už ve firmě máme', { x: 0.95, y: 2.65, w: 5.1, h: 0.35, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 12.5, color: AMBER, bold: true });
  s.addText('Odpovídá na otázku „jak to je".\n\nProjde síť, načte konfigurace a stav, a umí spočítat, kudy provoz reálně teče a kde se zahodí.', {
    x: 0.95, y: 3.05, w: 5.15, h: 1.9, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED });

  card(s, 6.85, 1.95, 5.85, 3.15);
  s.addText('NetBox', { x: 7.2, y: 2.2, w: 5.1, h: 0.45, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 22, bold: true, color: SLATE });
  s.addText('chceme doplnit', { x: 7.2, y: 2.65, w: 5.1, h: 0.35, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 12.5, color: AMBER, bold: true });
  s.addText('Odpovídá na otázku „jak to má být".\n\nDrží schválený stav, vlastníky, komunikační matici a historii kontrol. To IP Fabric ze své podstaty neví.', {
    x: 7.2, y: 3.05, w: 5.15, h: 1.9, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED });

  s.addText('Hodnota nevzniká v žádném z nich zvlášť. Vzniká porovnáním.', {
    x: 0.6, y: 5.55, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 17, bold: true, color: INK });
  s.addNotes('Tohle je věta, kterou si mají zapamatovat. Zopakuj ji.\n\nKdyby se někdo zeptal "a nestačí nám IP Fabric sám?": umí vlastní kontroly a je v tom dobrý. Neumí ale držet schválený stav v jazyce systémů a vlastníků a nedá se do něj pustit auditor ani vlastník aplikace. To je rozdíl mezi měřicím přístrojem a evidencí.');
}

/* ------------------------------------------------------------- 7 PILOT */
{
  const s = lightSlide('Co už je vyzkoušené', 'PILOT');
  s.addText('Postaveno a odladěno na vývojovém PC, s daty z veřejné demo sítě výrobce IP Fabricu. Import proběhl bez ručního zásahu.', {
    x: 0.6, y: 1.9, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 14, color: MUTED });
  const stats = [
    ['365', 'zařízení'],
    ['4 618', 'rozhraní'],
    ['1 713', 'IP adres'],
    ['21', 'lokalit'],
  ];
  stats.forEach((st, i) => {
    const cx = 0.6 + i * 3.1;
    card(s, cx, 2.6, 2.85, 1.7);
    s.addText(st[0], { x: cx + 0.25, y: 2.8, w: 2.35, h: 0.75, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 34, bold: true, color: SLATE });
    s.addText(st[1], { x: cx + 0.25, y: 3.6, w: 2.35, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 13, color: MUTED });
  });
  card(s, 0.6, 4.55, 12.1, 1.55);
  s.addText('Vše výše vzniklo automaticky z jednoho snímku sítě. Nikdo nic neopisoval, nic se needitovalo ručně. Stejný postup zafunguje na našem IP Fabricu — liší se jen adresa a přihlašovací údaje.', {
    x: 0.95, y: 4.85, w: 11.4, h: 1.0, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 14, color: MUTED });
  s.addNotes('Zdůrazni slovo AUTOMATICKY a slovo DEMO. Obojí musí zaznít v jedné větě, jinak si budou myslet, že je to naše síť.\n\nČíslo, které zabírá nejvíc: 4 618 rozhraní. Ručně by to nikdo nikdy nesepsal.');
}

/* --------------------------------------------------------- 8 JAK SE PLNI */
{
  const s = lightSlide('Jak se to plní daty', 'POSTUP');
  const kroky = [
    ['1', 'IP Fabric projde síť', 'Načte konfigurace a stav ze zařízení. Tuhle část už dnes provozujeme.'],
    ['2', 'Data se přenesou do NetBoxu', 'Automaticky, přes rozhraní. Bez ručního přepisování.'],
    ['3', 'Vznikne návrh změn', 'Import nezapisuje rovnou. Nejdřív ukáže, co by se změnilo, a to jde schválit.'],
    ['4', 'Změny se promítnou', 'Teprve po schválení. S historií, kdo a kdy.'],
  ];
  let y = 2.0;
  kroky.forEach(([n, h, t]) => {
    card(s, 0.6, y, 12.1, 0.95);
    s.addShape(pres.ShapeType.ellipse, { x: 0.95, y: y + 0.24, w: 0.46, h: 0.46, fill: { color: SLATE } });
    s.addText(n, { x: 0.95, y: y + 0.26, w: 0.46, h: 0.38, isTextBox: true, valign: 'middle', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: 'FFFFFF', align: 'center' });
    s.addText(h, { x: 1.65, y: y + 0.17, w: 3.9, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: INK });
    s.addText(t, { x: 5.7, y: y + 0.14, w: 6.7, h: 0.6, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED });
    y += 1.12;
  });
  s.addText('Celý běh na 8 000 záznamech trvá přibližně 25 minut a dá se spustit na plán, třeba každou noc.', {
    x: 0.6, y: 6.55, w: 12.1, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, italic: true, color: SLATE });
  s.addNotes('Krok 3 je ten, který vedení ocení nejvíc, i když to není vidět na první pohled: import nikdy nesahá do ostrých dat napřímo. Nejdřív návrh, pak schválení. Stejný princip, jaký znají z řízení změn.');
}

/* ------------------------------------------------------------ 9 MATICE */
{
  const s = lightSlide('Komunikační matice', 'JÁDRO PŘÍNOSU PRO KYBERNETICKOU BEZPEČNOST');
  card(s, 0.6, 1.9, 5.85, 3.65);
  s.addText('Co to je', { x: 0.95, y: 2.15, w: 5.1, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 18, bold: true, color: INK });
  s.addText('Seznam tvrzení o tom, co spolu smí a nesmí komunikovat. Vzniká z architektury aplikací a od vlastníků systémů — není to síťový dokument, je to rozhodnutí firmy.\n\nDnes taková tabulka neexistuje. Její sepsání je největší kus práce celého zavedení a nenahradí ho žádný nástroj.', {
    x: 0.95, y: 2.6, w: 5.15, h: 2.85, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED });

  card(s, 6.85, 1.9, 5.85, 3.65);
  s.addText('Co s ní umíme', { x: 7.2, y: 2.15, w: 5.1, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 18, bold: true, color: INK });
  s.addText('Každý řádek matice se ověří simulací cesty v IP Fabricu a porovná se skutečností. Nic se přitom do sítě neposílá.\n\nVýstupem je seznam rozporů s časem, odpovědností a historií. Kontrola se dá pustit opakovaně a sledovat vývoj.', {
    x: 7.2, y: 2.6, w: 5.15, h: 2.85, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED });
  s.addNotes('Buď tady maximálně poctivý: sepsání matice je práce lidí a bude to bolet. Když to zamlčíš a vyjde to najevo za půl roku, přijdeš o kredit. Když to řekneš teď, vypadá to jako realistický plán, ne jako prodej.');
}

/* ------------------------------------------------------------ 10 VERDIKTY */
{
  const s = lightSlide('„Neprojde" nejsou dvě slova, ale tři situace', 'JAK SE ČTE VÝSLEDEK');
  const v = [
    ['V POŘÁDKU', OK, 'Skutečnost odpovídá matici.', 'Neřeší nikdo'],
    ['PORUŠENÍ MATICE', BAD, 'Zakázaná komunikace prochází.', 'Řeší bezpečnost'],
    ['CHYBÍ PRAVIDLO', WARN, 'Povolenou komunikaci zahodil firewall.', 'Řeší správce pravidel'],
    ['NEDOSTUPNÉ', ROUTE, 'Zahozeno bez účasti firewallu — chybí trasa.', 'Řeší síťař'],
  ];
  v.forEach((it, i) => {
    const cx = 0.6 + (i % 2) * 6.25;
    const cy = 2.0 + Math.floor(i / 2) * 2.1;
    card(s, cx, cy, 5.85, 1.8);
    s.addShape(pres.ShapeType.rect, { x: cx + 0.35, y: cy + 0.35, w: 0.16, h: 0.16, fill: { color: it[1] } });
    s.addText(it[0], { x: cx + 0.65, y: cy + 0.22, w: 5.0, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: it[1] });
    s.addText(it[2], { x: cx + 0.65, y: cy + 0.68, w: 5.0, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 13, color: MUTED });
    s.addText(it[3], { x: cx + 0.65, y: cy + 1.24, w: 5.0, h: 0.35, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12, bold: true, color: INK });
  });
  s.addText('Poslední kategorii nenajde žádná analýza firewallových pravidel — rozbitá služba, o které firewall vůbec neví.', {
    x: 0.6, y: 6.35, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 14, italic: true, color: SLATE });
  s.addNotes('Tady zpomal. Tohle je intelektuální jádro celé prezentace a zároveň to, čím se odlišíš od běžné prezentace o nástroji.\n\nPříklad na dokreslení: služba, která jedním směrem funguje a druhým ne, protože chybí trasa zpátky. Firewall to neukáže, protože se k němu provoz vůbec nedostane.');
}

/* ------------------------------------------------------------- 11 NALEZY */
{
  const s = lightSlide('Co kontrola našla na demo síti', 'UKÁZKA METODY — NE NAŠE SÍŤ');
  s.addText('Čtyřicet řádků matice, jeden běh, necelá minuta. Nálezy níže pocházejí z veřejné demo sítě výrobce, ne ze Správy železnic.', {
    x: 0.6, y: 1.85, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, color: MUTED });
  const rows = [
    [{ text: 'Nález', options: { bold: true } }, { text: 'Zjištění', options: { bold: true } }, { text: 'Kategorie', options: { bold: true } }],
    ['Telnet otevřený na prvcích správy', 'Nešifrovaná správa je průchozí, včetně firewallu', 'Porušení matice'],
    ['SSH z cloudu do vnitřní sítě', 'Provoz projde přes tři pravidla až k cíli', 'Porušení matice'],
    ['Sdílení souborů mezi pobočkami', 'Prochází přes páteř, matice to zakazuje', 'Porušení matice'],
    ['Služba funguje jen jedním směrem', 'Zpět chybí trasa, firewall v tom nefiguruje', 'Nedostupné'],
    ['Správa firewallu z jádra nefunguje', 'Zahozeno na prvním prvku, nikdo o tom neví', 'Nedostupné'],
  ];
  s.addTable(rows, {
    x: 0.6, y: 2.5, w: 12.1, colW: [4.0, 5.3, 2.8],
    fontFace: BODY, fontSize: 12.5, color: MUTED,
    border: { type: 'solid', color: LINE, pt: 0.75 },
    fill: { color: CARD }, rowH: 0.52, valign: 'middle',
    margin: [6, 10, 6, 10],
  });
  s.addText('Takhle vypadá výsledek na síti, kterou nikdo předtím takto nezkontroloval. Naši síť zatím nikdo nezkontroloval vůbec.', {
    x: 0.6, y: 6.2, w: 12.1, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 15, bold: true, color: INK });
  s.addNotes('Poslední věta je nejsilnější moment celé prezentace. Řekni ji pomalu a nech chvíli ticho.\n\nPokud se zeptají "a co by to našlo u nás?" — odpověz upřímně: nevím, a právě proto o to žádám. Nikdy neslibuj konkrétní počet nálezů.');
}

/* --------------------------------------------------------- 12 CO DAL UMI */
{
  const s = lightSlide('Co z toho vyroste dál', 'VÝHLED');
  const items = [
    ['Analýza sítě před změnou', 'Co je na co navázané, koho se zásah dotkne, co se stane při výpadku prvku. Odpověď z evidence místo obvolávání.'],
    ['Návrh změn nanečisto', 'Změna se dá namodelovat stranou, prohlédnout jako rozdíl a teprve pak schválit. Stejný mechanismus, jakým probíhá import.'],
    ['Pravidelná kontrola bez člověka', 'Kontrola matice běží na plán. Když někdo otevře pravidlo, které tam nepatří, víme to ráno, ne u příštího auditu.'],
    ['Podklady pro audit na jedno kliknutí', 'Kdy se kontrolovalo, co vyšlo, kdo to spustil. Historie je vedlejší produkt provozu, ne zvláštní úkol.'],
  ];
  let y = 1.9;
  items.forEach((it) => {
    card(s, 0.6, y, 12.1, 1.1);
    dot(s, 0.95, y + 0.29);
    s.addText(it[0], { x: 1.25, y: y + 0.18, w: 4.3, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: INK });
    s.addText(it[1], { x: 5.7, y: y + 0.15, w: 6.7, h: 0.8, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED });
    y += 1.28;
  });
  s.addNotes('Nezdržuj se tu dlouho. Je to slide "co bude, až to poběží" — vedení potřebuje vidět, že to není jednorázový projekt, ale schopnost, která zůstane.');
}

/* --------------------------------------------------------- 13 DATA DOMA */
{
  const s = darkSlide();
  s.addText('CITLIVOST DAT', { x: 0.9, y: 0.75, w: 8, h: 0.3, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 11, bold: true, color: AMBER, charSpacing: 2 });
  s.addText('Kompletní popis sítě je citlivý dokument.\nProto zůstane u nás.', {
    x: 0.9, y: 1.2, w: 11.4, h: 1.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 29, bold: true, color: 'FFFFFF', lineSpacing: 36 });
  const body = [
    ['Vlastní server ve vnitřní síti', 'Žádná cloudová služba, žádný externí provozovatel, žádné odesílání dat ven.'],
    ['Vlastní databáze a zálohy', 'Data i zálohy leží na našich discích, pod našimi pravidly pro uchovávání.'],
    ['Přístup jen pro určené role', 'NetBox má vlastní správu oprávnění — kdo co vidí a kdo smí měnit, se nastavuje po skupinách.'],
    ['Otevřený kód znamená kontrolu', 'Nikdo neposílá telemetrii, kterou bychom neviděli. Kód je veřejný a auditovatelný.'],
  ];
  let y = 3.05;
  body.forEach(([h, t]) => {
    s.addShape(pres.ShapeType.rect, { x: 0.95, y: y + 0.14, w: 0.13, h: 0.13, fill: { color: AMBER } });
    s.addText(h, { x: 1.3, y: y, w: 4.3, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: 'FFFFFF' });
    s.addText(t, { x: 5.8, y: y - 0.05, w: 6.6, h: 0.65, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: 'B9C8CD' });
    y += 0.95;
  });
  s.addNotes('Tenhle slide je odpověď na námitku dřív, než zazní. Kompletní mapa sítě je přesně to, co by útočník chtěl — a právě proto ji nechceme nikde venku.\n\nZároveň je to argument pro otevřený zdroj, ne proti němu: u uzavřeného produktu nevíš, co posílá domů.');
}

/* ------------------------------------------------------------- 14 NAKLADY */
{
  const s = lightSlide('Co to bude stát', 'NÁKLADY — POCTIVĚ');
  const rows = [
    [{ text: 'Položka', options: { bold: true } }, { text: 'Náklad', options: { bold: true } }, { text: 'Poznámka', options: { bold: true } }],
    ['Licence NetBox', '0 Kč', 'Otevřený software, Apache 2.0'],
    ['IP Fabric', '0 Kč navíc', 'Máme, využijeme stávající licenci'],
    ['Server', 'jeden virtuál', '4 jádra, 8 GB RAM, 100 GB disku'],
    ['Zálohování', 'v rámci stávajícího', 'Databáze a konfigurace, denně'],
    ['Provoz a aktualizace', 'jednotky hodin měsíčně', 'Aktualizace dvakrát až čtyřikrát ročně'],
    ['Sestavení matice', 'největší položka', 'Práce vlastníků systémů, ne nástroje'],
  ];
  s.addTable(rows, {
    x: 0.6, y: 2.0, w: 12.1, colW: [4.0, 3.2, 4.9],
    fontFace: BODY, fontSize: 13, color: MUTED,
    border: { type: 'solid', color: LINE, pt: 0.75 },
    fill: { color: CARD }, rowH: 0.52, valign: 'middle',
    margin: [6, 10, 6, 10],
  });
  s.addText('Neskrývám poslední řádek. Nástroj je zdarma, práce není — a je to práce, kterou kvůli regulaci odvedeme i tak.', {
    x: 0.6, y: 6.15, w: 12.1, h: 0.6, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 15, bold: true, color: INK });
  s.addNotes('Poslední řádek je záměrně v tabulce. Kdybys ho vynechal a někdo se zeptá, vypadá to, že jsi to schoval. Takhle vypadáš jako člověk, který ví, do čeho jde.\n\nČísla u serveru si před jednáním ověř podle toho, co je zvykem u nás — ať nesedí vedle člověka z provozu a nekroutí hlavou.');
}

/* ------------------------------------------------------------- 15 RIZIKA */
{
  const s = lightSlide('Rizika a jak je řešíme', 'CO MŮŽE NEVYJÍT');
  const items = [
    ['„Otevřený software nemá podporu."', 'Komunitní vydání má dokumentaci i širokou komunitu. Placená podpora od výrobce existuje a dá se dokoupit, když ji budeme chtít — není podmínkou provozu.'],
    ['„Bude na tom viset jeden člověk."', 'Postup je zdokumentovaný, instalace je standardní kontejnerová a znalost NetBoxu je běžně dostupná na trhu. Dokumentace vzniká průběžně, ne až na konci.'],
    ['„Data budou zastaralá."', 'Import běží automaticky na plán z IP Fabricu. Zastarat může jen to, co plníme ručně — a to je právě matice, kde se počítá s pravidelnou revizí.'],
    ['„Nikdo to nebude používat."', 'Proto začínáme kontrolou matice, ne budováním evidence pro evidenci. První výstup je seznam konkrétních nálezů, ne prázdná databáze.'],
  ];
  let y = 1.9;
  items.forEach((it) => {
    card(s, 0.6, y, 12.1, 1.1);
    s.addText(it[0], { x: 0.95, y: y + 0.13, w: 4.0, h: 0.8, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 14, bold: true, italic: true, color: BAD });
    s.addText(it[1], { x: 5.2, y: y + 0.16, w: 7.2, h: 0.85, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED });
    y += 1.28;
  });
  s.addNotes('Vytáhni námitky sám dřív, než je vytáhnou oni. Kdo si připraví protiargumenty, působí připraveně; kdo se nechá zaskočit, působí nadšeně.');
}

/* -------------------------------------------------------------- 16 PROVOZ */
{
  const s = lightSlide('Jak se to provozuje', 'ÚDRŽBA, ZÁLOHY, PŘÍSTUP');
  const cols = [
    ['Aktualizace', 'Nová verze NetBoxu vychází přibližně čtvrtletně. Aktualizace je výměna kontejneru a migrace databáze, řádově desítky minut, s možností vrátit se zpět.\n\nNemusí se aktualizovat každá verze — držíme se stabilní řady.'],
    ['Zálohy', 'Zálohuje se databáze a konfigurace. Obojí je malé, řádově stovky megabajtů, a zapadne do stávajícího zálohovacího režimu.\n\nObnova je nasazení zálohy do čistého kontejneru, vyzkoušené.'],
    ['Přístup', 'Přes webové rozhraní ve vnitřní síti, s přihlášením. Oprávnění se řídí po skupinách a dají se navázat na doménové účty.\n\nČtenářský přístup pro audit či vlastníky aplikací je bez rizika.'],
  ];
  cols.forEach((c, i) => {
    const cx = 0.6 + i * 4.13;
    card(s, cx, 1.95, 3.85, 3.95);
    dot(s, cx + 0.32, 2.26);
    s.addText(c[0], { x: cx + 0.6, y: 2.12, w: 3.0, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 17, bold: true, color: INK });
    s.addText(c[1], { x: cx + 0.32, y: 2.6, w: 3.25, h: 3.2, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12, color: MUTED });
  });
  s.addNotes('Tenhle slide je pro provozní lidi v místnosti. Vedení ho přejde, ale kdyby chyběl, provozní by námitku vznesl a rozhodnutí by se odložilo.');
}

/* --------------------------------------------------------------- 17 PLAN */
{
  const s = lightSlide('Plán zavedení', 'CO A KDY');
  const faze = [
    ['Fáze 1', '4–6 týdnů', 'Server a první data', 'Instalace ve vnitřní síti, napojení na firemní IP Fabric, první automatický import, ověření inventáře proti skutečnosti.'],
    ['Fáze 2', '6–10 týdnů', 'Matice a první kontrola', 'Sestavení komunikační matice s vlastníky systémů, první běh kontroly, vyhodnocení nálezů s bezpečností.'],
    ['Fáze 3', 'průběžně', 'Pravidelný provoz', 'Kontrola na plán, reporty pro kybernetickou bezpečnost, postupné rozšiřování o další segmenty a zdroje dat.'],
  ];
  let y = 2.0;
  faze.forEach((f) => {
    card(s, 0.6, y, 12.1, 1.4);
    s.addText(f[0], { x: 0.95, y: y + 0.25, w: 1.5, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 17, bold: true, color: SLATE });
    s.addText(f[1], { x: 0.95, y: y + 0.68, w: 1.5, h: 0.35, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12, bold: true, color: AMBER });
    s.addText(f[2], { x: 2.6, y: y + 0.25, w: 2.9, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 15, bold: true, color: INK });
    s.addText(f[3], { x: 5.65, y: y + 0.2, w: 6.75, h: 0.95, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: MUTED });
    y += 1.57;
  });
  s.addText('První hmatatelný výstup — seznam nálezů z naší vlastní sítě — je na konci fáze 2.', {
    x: 0.6, y: 6.8, w: 12.1, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 13.5, italic: true, color: SLATE });
  s.addNotes('Termíny jsou odhad a řekni to tak. Fáze 2 závisí na tom, jak rychle se podaří dostat dohromady vlastníky systémů — to není v tvých rukou a je poctivé to přiznat.');
}

/* ------------------------------------------------------------ 18 ZADOST */
{
  const s = darkSlide();
  s.addText('ROZHODNUTÍ', { x: 0.9, y: 0.8, w: 8, h: 0.3, isTextBox: true, valign: 'top', margin: 0,
    fontFace: BODY, fontSize: 11, bold: true, color: AMBER, charSpacing: 2 });
  s.addText('O co žádáme', { x: 0.9, y: 1.25, w: 10, h: 0.9, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 36, bold: true, color: 'FFFFFF' });
  const asks = [
    ['Jeden virtuální server', 've vnitřní síti, zařazený do stávajícího zálohování'],
    ['Čtenářský přístup k IP Fabricu', 'servisní účet s právem číst data přes rozhraní'],
    ['Vyčleněný čas a garanta', 'část úvazku na zavedení a odpovědnou osobu z bezpečnosti'],
  ];
  let y = 2.7;
  asks.forEach((a, i) => {
    s.addShape(pres.ShapeType.roundRect, { x: 0.9, y, w: 11.5, h: 1.05, rectRadius: 0.04,
      fill: { color: '1F323C' }, line: { color: SLATE, width: 0.75 } });
    s.addText(String(i + 1), { x: 1.25, y: y + 0.25, w: 0.5, h: 0.55, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 24, bold: true, color: AMBER });
    s.addText(a[0], { x: 1.95, y: y + 0.18, w: 4.6, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: HEAD, fontSize: 16, bold: true, color: 'FFFFFF' });
    s.addText(a[1], { x: 1.95, y: y + 0.58, w: 9.9, h: 0.4, isTextBox: true, valign: 'top', margin: 0,
      fontFace: BODY, fontSize: 12.5, color: 'B9C8CD' });
    y += 1.25;
  });
  s.addText('Žádné licenční náklady. Žádná data mimo firmu. První výsledky do konce druhé fáze.', {
    x: 0.9, y: 6.55, w: 11.5, h: 0.5, isTextBox: true, valign: 'top', margin: 0,
    fontFace: HEAD, fontSize: 16, bold: true, color: AMBER });
  s.addNotes('Skonči tímhle slidem a nech ho na plátně během diskuse. Tři konkrétní věci, nic vágního.\n\nKdyby došlo na "kolik to bude stát celkem" — vrať se na slide s náklady a zopakuj, že největší položka je práce, kterou kvůli regulaci odvedeme tak jako tak.');
}

pres.writeFile({ fileName: 'netbox-sz-vedeni.pptx' })
  .then(f => console.log('hotovo:', f));
