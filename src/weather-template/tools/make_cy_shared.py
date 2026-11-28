"""Write cy-shared.json: the Welsh lines both Welsh weather boards share (27 Nov 2026).

    python3 tools/make_cy_shared.py parts/cy-shared.json <Ammanford W as JSON> parts/cy-shared.json

The Ammanford W dump is the page's `var W=` dictionary (the CYW data block) saved as JSON;
keys it already has are left out. Re-running keeps every line already in cy-shared.json.

Keys are the engine's tokenised English: {P} place (mutated by the word before it), {P} place
unmutated, {Px} place dropped, {D} date, {X} weather word / wind direction / pollutant (already
Welsh), {Q} a data name, {L} a list of data names, # numbers in order. Welsh must keep the numbers
in the same order as the English, because they are filled in turn.

All Welsh here is a draft: not checked by a Welsh speaker.
Keys Ammanford's own dictionary already has are left out, so this file never changes a line
Ammanford already shows.
"""
import json
import sys

D = {}
BOTH = set()   # keys Ammanford's page also needs (its own chart code writes the rest of its Welsh)


def add(en, cy, both=False):
    if en in D and D[en] != cy:
        raise SystemExit(f"two Welsh lines for {en!r}")
    D[en] = cy
    if both:
        BOTH.add(en)


HOURS = [("# hours old", "# awr oed")]  # "# hour old" is looked up as this (agree() in parts/cy.js)
TREND = [("rising", "yn codi"), ("falling", "yn gostwng"), ("steady", "yn sefydlog")]

# ---------------------------------------------------------------- weather story
for en, cy in [
    ("What this tells us", "Beth mae hyn yn ei ddweud wrthym"),
    ("It's {X} in {P} at #°C, but it feels more like #°C.", "Ar hyn o bryd yn {P}: {X}, #°C, ond mae’n teimlo’n debycach i #°C."),
    ("It's {X} in {P} at #°C.", "Ar hyn o bryd yn {P}: {X}, #°C."),
    ("Conditions in {P} at #°C, but it feels more like #°C.", "Ar hyn o bryd yn {P}: #°C, ond mae’n teimlo’n debycach i #°C."),
    ("Conditions in {P} at #°C.", "Ar hyn o bryd yn {P}: #°C."),
    ("Rain looks likely now (#% chance).", "Mae glaw yn debygol nawr (siawns o #%)."),
    ("Rain looks likely from #:# (#% chance).", "Mae glaw yn debygol o #:# ymlaen (siawns o #%)."),
    ("A shower is possible, with the chance peaking at #% around #:#.", "Mae cawod yn bosibl, gyda’r siawns ar ei huchaf, sef #%, tua #:#."),
    ("It should stay mostly dry, with a rain chance of at most #% (around #:#).", "Dylai aros yn sych gan fwyaf, gyda siawns o law o #% ar y mwyaf (tua #:#)."),
    ("It should stay dry for the rest of today.", "Dylai aros yn sych am weddill heddiw."),
    ("Forecast figures for {P} are not available right now.", "Nid yw ffigurau’r rhagolwg ar gyfer {P} ar gael ar hyn o bryd."),
    ("Hour-by-hour detail is not available for today, but the daily forecast for {P} is a high of #°C and a low of #°C, with a #% chance of rain and gusts up to # km/h.",
     "Nid yw manylion awr wrth awr ar gael ar gyfer heddiw, ond mae’r rhagolwg dyddiol ar gyfer {P} yn rhoi uchafswm o #°C ac isafswm o #°C, gyda #% o siawns o law a hyrddiau hyd at # km/a."),
    ("Sunrise #:# · sunset #:#.", "Codiad haul #:# · machlud #:#."),
    ("The sun or moon is drawn where it is now; clouds, rain and wind follow the forecast for this hour; the Moon shows its real phase.",
     "Mae’r haul neu’r lleuad yn cael eu tynnu lle maent nawr; mae’r cymylau, y glaw a’r gwynt yn dilyn y rhagolwg ar gyfer yr awr hon; mae’r lleuad yn dangos ei gwedd go iawn."),
    ("Sunrise and sunset times are not available, so no sun or moon is drawn.", "Nid yw amserau codiad a machlud haul ar gael, felly ni thynnir haul na lleuad."),
    ("Clouds, rain and wind follow the forecast.", "Mae’r cymylau, y glaw a’r gwynt yn dilyn y rhagolwg."),
    ("#:#:# GMT", "#:#:# GMT"), ("#:#:# BST", "#:#:# BST"),
    ("Hour by hour", "Awr wrth awr"),
    ("Today: high #°C at #:#, low #°C at #:#; rain chance peaks at #% at #:#; strongest gusts # km/h at #:#.",
     "Heddiw: uchaf #°C am #:#, isaf #°C am #:#; siawns o law ar ei huchaf, sef #%, am #:#; hyrddiau cryfaf # km/a am #:#."),
    ("Swipe sideways for the whole day; the grey bands are night.", "Llithrwch i’r ochr i weld y diwrnod cyfan; y bandiau llwyd yw’r nos."),
    ("Chance of rain %", "Siawns o law %"), ("Wind km/h", "Gwynt km/a"),
    ("Arrows point where the wind is blowing to; colour shows gusts: blue-green under # km/h, amber # to #, red # or more.",
     "Mae’r saethau’n pwyntio i ble mae’r gwynt yn chwythu; mae’r lliw yn dangos hyrddiau: glas-wyrdd o dan # km/a, ambr # i #, coch # neu fwy."),
    ("Figures are Open-Meteo model values.", "Gwerthoedd model Open-Meteo yw’r ffigurau."),
    ("Detailed chart: humidity, cloud cover and feels-like", "Siart manwl: lleithder, gorchudd cwmwl a theimlo fel"),
    ("#mm", "#mm"),

    ("The week at a glance", "Yr wythnos ar gip"),
    ("Low to high temperature for each day on one shared scale (#° to #°).", "Tymheredd isaf i uchaf pob diwrnod ar un raddfa gyffredin (#° i #°)."),
    ("Warmest day: {D} (#°).", "Y diwrnod cynhesaf: {D} (#°)."),
    ("Highest rain chance: {D} (#%).", "Y siawns uchaf o law: {D} (#%)."),
    ("Warmest day: today (#°).", "Y diwrnod cynhesaf: heddiw (#°)."),
    ("Highest rain chance: today (#%).", "Y siawns uchaf o law: heddiw (#%)."),
    ("colder", "oerach"), ("warmer", "cynhesach"),
    ("Seven-day temperature ranges", "Ystodau tymheredd saith diwrnod"),
    ("The sun is up (sunrise #:#, sunset #:#).", "Mae’r haul i fyny (codiad haul #:#, machlud #:#)."),
    ("The sun is down (sunrise #:#, sunset #:#).", "Mae’r haul i lawr (codiad haul #:#, machlud #:#)."),
    ("Sunrise and sunset times are not available.", "Nid yw amserau codiad a machlud haul ar gael."),
    ("Hour-by-hour chart, scrolls sideways", "Siart awr wrth awr, yn sgrolio i’r ochr"),
    ("Hour-by-hour chart for today.", "Siart awr wrth awr ar gyfer heddiw."),
    ("Location", "Lleoliad"),
]:
    add(en, cy)

for h_en, h_cy in HOURS:
    add(f"(This forecast snapshot is from #:#, {h_en}.)", f"(Mae’r ciplun rhagolwg hwn o #:#, {h_cy}.)")

# the wind: with or without a direction, three endings (NPT's exposed wording is its CFG.exposed)
WEND = [(", so it will feel blustery, especially on the coast and the high ground.", ", felly bydd yn wyntog iawn, yn enwedig ar yr arfordir ac ar dir uchel."),
        (", so it will feel blustery, especially on higher ground.", ", felly bydd yn wyntog iawn, yn enwedig ar dir uchel."),
        (", so it will feel breezy.", ", felly bydd yn awelog."),
        (", so it stays fairly calm.", ", felly mae’n weddol dawel.")]
for e_en, e_cy in WEND:
    add("The wind is from the {X} at # km/h, with gusts reaching # km/h around #:#" + e_en,
        "Mae’r gwynt yn chwythu o’r {X} ar # km/a, gyda hyrddiau hyd at # km/a tua #:#" + e_cy)
    add("The wind is at # km/h, with gusts reaching # km/h around #:#" + e_en,
        "Mae’r gwynt yn # km/a, gyda hyrddiau hyd at # km/a tua #:#" + e_cy)

# the sky picture's label (NPT: "the Neath Port Talbot coast and hills")
for over_en, over_cy in [("the {P} coast and hills", "arfordir a bryniau {P}"), ("the valley", "y cwm")]:
    pre_en, pre_cy = f"Illustration of the sky over {over_en} at #:#: ", f"Darlun o’r awyr dros {over_cy} am #:#: "
    add(pre_en + "{X} (#% cloud cover), #°C, #% chance of rain, wind from the {X} # km/h.",
        pre_cy + "{X} (#% o orchudd cwmwl), #°C, #% o siawns o law, gwynt o’r {X} # km/a.")
    add(pre_en + "{X} (#% cloud cover), #°C, #% chance of rain, wind # km/h.",
        pre_cy + "{X} (#% o orchudd cwmwl), #°C, #% o siawns o law, gwynt # km/a.")
    add(pre_en + "{X}, #% chance of rain, wind up to # km/h (daily forecast; hourly detail is not available).",
        pre_cy + "{X}, #% o siawns o law, gwynt hyd at # km/a (rhagolwg dyddiol; nid yw manylion yr awr ar gael).")
    add(pre_en + "daily forecast, #% chance of rain, wind up to # km/h (daily forecast; hourly detail is not available).",
        pre_cy + "rhagolwg dyddiol, #% o siawns o law, gwynt hyd at # km/a (nid yw manylion yr awr ar gael).")
    add(pre_en + "no forecast figures available.", pre_cy + "dim ffigurau rhagolwg ar gael.")

# ---------------------------------------------------------------- air
AQL = [("Low", "Isel"), ("Moderate", "Cymedrol"), ("High", "Uchel"), ("Very High", "Uchel iawn"), ("Very high", "Uchel iawn")]
for en, cy in [
    ("The air-quality index is", "Mae’r mynegai ansawdd aer yn"),
    ("That station is about # km {X} of {P}, so treat this as a regional picture rather than {P} itself.",
     "Mae’r orsaf tua # km i’r {X} o {P}, felly darlun rhanbarthol yw hwn, nid {P} ei hun."),
    ("Most people:", "Y rhan fwyaf o bobl:"),
    ("If you have asthma, or a heart or lung condition:", "Os oes gennych asthma, neu gyflwr ar y galon neu’r ysgyfaint:"),
    ("Enjoy your usual outdoor activities.", "Mwynhewch eich gweithgareddau awyr agored arferol."),
    ("Health advice: Defra Daily Air Quality Index", "Cyngor iechyd: Mynegai Ansawdd Aer Dyddiol Defra"),
    ("Index # to # at {Q}.", "Mynegai # i # yn {Q}."),
    ("Bars below show each pollutant on the same # to # scale (ozone is an #-hour mean, particles a #-hour mean).",
     "Mae’r bariau isod yn dangos pob llygrydd ar yr un raddfa # i # (cymedr #-awr yw osôn, cymedr #-awr yw gronynnau)."),
    ("{Q}", "{Q}"),
    ("index at {Q}", "mynegai yn {Q}"),
    ("Hourly readings from Defra's UK-AIR network (data provisional and unvalidated; Open Government Licence v#).",
     "Darlleniadau fesul awr o rwydwaith UK-AIR Defra (data dros dro, heb eu dilysu; Trwydded Llywodraeth Agored v#)."),
    ("{Q}, near the steelworks, is the only Defra station in the borough, so it stands in for every town on this page.",
     "{Q}, ger y gwaith dur, yw’r unig orsaf Defra yn y fwrdeistref, felly mae’n cynrychioli pob tref ar y dudalen hon."),
    ("NO₂ is the latest hour, ozone an #-hour mean and particles #-hour means.", "NO₂ yw’r awr ddiwethaf, cymedr #-awr yw osôn a chymedrau #-awr yw gronynnau."),
    ("Index uses the UK Daily Air Quality Index: ## Low, ## Moderate, ## High, # Very High.",
     "Mae’r mynegai’n defnyddio Mynegai Ansawdd Aer Dyddiol y DU: ## Isel, ## Cymedrol, ## Uchel, # Uchel Iawn."),
    ("Index for each pollutant", "Mynegai ar gyfer pob llygrydd"),
    ("Air-quality readings are not available in this copy of the page.", "Nid yw darlleniadau ansawdd aer ar gael yn y copi hwn o’r dudalen."),
    ("No usable air-quality reading is available from {Q} right now, so no index is shown.",
     "Nid oes darlleniad ansawdd aer defnyddiadwy ar gael o {Q} ar hyn o bryd, felly ni ddangosir mynegai."),
    ("Air quality index not available", "Mynegai ansawdd aer ddim ar gael"),
    ("{X}: index #", "{X}: mynegai #"), ("{X}: no reading", "{X}: dim darlleniad"), ("{X}: not measured here", "{X}: heb ei fesur yma"),
    ("no reading", "dim darlleniad"), ("not measured here", "heb ei fesur yma"),
    ("This station does not measure {X}, so the index covers {X}, {X} and {X} only.", "Nid yw’r orsaf hon yn mesur {X}, felly mae’r mynegai’n cwmpasu {X}, {X} a {X} yn unig."),
    ("This station does not measure {X} or {X}, so the index covers {X} and {X} only.", "Nid yw’r orsaf hon yn mesur {X} na {X}, felly mae’r mynegai’n cwmpasu {X} a {X} yn unig."),
    ("This station does not measure {X}, {X} or {X}, so the index covers {X} only.", "Nid yw’r orsaf hon yn mesur {X}, {X} na {X}, felly mae’r mynegai’n cwmpasu {X} yn unig."),
    ("There is no reading for {X} this hour, so it is left out.", "Nid oes darlleniad ar gyfer {X} yr awr hon, felly mae wedi’i adael allan."),
    ("There is no reading for {X} or {X} this hour, so it is left out.", "Nid oes darlleniad ar gyfer {X} na {X} yr awr hon, felly maent wedi’u gadael allan."),
    ("The nearest station, {Q}, has no usable reading right now.", "Nid oes darlleniad defnyddiadwy ar hyn o bryd o’r orsaf agosaf, {Q}."),
]:
    add(en, cy)
for lab, lab_cy in AQL:
    add(f"# out of # ({lab})", f"# allan o # ({lab_cy})")
    add(f"Air quality index # out of #, {lab}, at {{Q}}.", f"Mynegai ansawdd aer # allan o #, {lab_cy}, yn {{Q}}.")
    add(f"{{Q}} (# km {{X}}) is at # ({lab}).", f"Mae {{Q}} (# km i’r {{X}}) ar # ({lab_cy}).")
    for tail_en, tail_cy in [(" and does measure {X}.", " ac mae’n mesur {X}."), (" and does measure {X} and {X}.", " ac mae’n mesur {X} a {X}.")]:
        add(f"{{Q}} (# km {{X}}) is at # ({lab})" + tail_en, f"Mae {{Q}} (# km i’r {{X}}) ar # ({lab_cy})" + tail_cy)
# "at NAME[, though that reading is from 17:00, 2 hours old], and ... ."
for age_en, age_cy in [("", "")] + [(f", though that reading is from #:#, {h}", f", er bod y darlleniad hwnnw o #:#, {c}") for h, c in HOURS]:
    for end_en, end_cy in [(", and all pollutants are low.", ", ac mae pob llygrydd yn isel."),
                           (", and {X} is setting the score.", ", a {X} sy’n pennu’r sgôr."),
                           (", and {X} and {X} are setting the score.", ", a {X} a {X} sy’n pennu’r sgôr."),
                           (", and {X} and {X} and {X} are setting the score.", ", a {X}, {X} a {X} sy’n pennu’r sgôr.")]:
        add("at {Q}" + age_en + end_en, "yn {Q}" + age_cy + end_cy)
# Defra advice, sentence by sentence, in the Welsh Ammanford's own chart code uses (ADV / ADVC)
ADV = ["Adults and children with lung problems, and adults with heart problems, who experience symptoms, should consider reducing strenuous physical activity, particularly outdoors.",
       "Anyone experiencing discomfort such as sore eyes, cough or sore throat should consider reducing activity, particularly outdoors.",
       "Adults and children with lung problems, and adults with heart problems, should reduce strenuous physical exertion, particularly outdoors, and particularly if they experience symptoms.",
       "People with asthma may find they need to use their reliever inhaler more often.",
       "Older people should also reduce physical exertion.",
       "Reduce physical exertion, particularly outdoors, especially if you experience symptoms such as cough or sore throat.",
       "Adults and children with lung problems, adults with heart problems, and older people, should avoid strenuous physical activity."]
ADVC = ["Dylai oedolion a phlant sydd â phroblemau ysgyfaint, ac oedolion â phroblemau’r galon, sy’n profi symptomau, ystyried lleihau gweithgarwch corfforol egnïol, yn enwedig yn yr awyr agored.",
        "Dylai unrhyw un sy’n profi anghysur fel dolur llygaid, peswch neu ddolur gwddf ystyried lleihau gweithgarwch, yn enwedig yn yr awyr agored.",
        "Dylai oedolion a phlant sydd â phroblemau ysgyfaint, ac oedolion â phroblemau’r galon, leihau ymdrech gorfforol egnïol, yn enwedig yn yr awyr agored, ac yn enwedig os ydynt yn profi symptomau.",
        "Efallai y bydd pobl ag asthma angen defnyddio eu hanadlydd lliniaru yn amlach.",
        "Dylai pobl hŷn hefyd leihau ymdrech gorfforol.",
        "Lleihewch ymdrech gorfforol, yn enwedig yn yr awyr agored, yn enwedig os ydych yn profi symptomau fel peswch neu ddolur gwddf.",
        "Dylai oedolion a phlant sydd â phroblemau ysgyfaint, oedolion â phroblemau’r galon, a phobl hŷn osgoi gweithgarwch corfforol egnïol."]
for en, cy in zip(ADV, ADVC):
    add(en.replace("2.5", "#").replace("10", "#"), cy)

# ---------------------------------------------------------------- rivers (NPT: shared viz-core with CFG.rng "usual")
POS = [("below its usual range", "islaw ei hystod arferol"), ("above its usual range", "uwchlaw ei hystod arferol"),
       ("in the lower part of its usual range", "yn rhan isaf ei hystod arferol"),
       ("in the middle of its usual range", "yng nghanol ei hystod arferol"),
       ("in the upper part of its usual range", "yn rhan uchaf ei hystod arferol")]
READ = [("", "")] + [(f" (reading from #:#, {h})", f" (darlleniad o #:#, {c})") for h, c in HOURS]
for en, cy in [
    ("River level readings are not available right now.", "Nid oes darlleniadau lefel afonydd ar gael ar hyn o bryd."),
    (", the nearest gauge (# km from {P}), reads", ", y medrydd agosaf (# km o {P}), yn darllen"),
    (".", "."),
    ("These are level readings, not a flood forecast.", "Darlleniadau lefel yw’r rhain, nid rhagolwg llifogydd."),
    ("How high is each river", "Pa mor uchel yw pob afon"),
    ("Each bar is that gauge's own scale: the shaded middle is its usual range (where NRW data gives one), and the dot is the latest reading.",
     "Mae pob bar ar raddfa’r medrydd ei hun: y canol cysgodol yw ei ystod arferol (lle mae data CNC yn rhoi un), a’r pwynt yw’r darlleniad diweddaraf."),
    ("The thin line shows readings collected over the last # hours.", "Mae’r llinell denau yn dangos y darlleniadau a gasglwyd dros y # awr diwethaf."),
    ("Tidal gauges move with the tide and have no usual range.", "Mae medryddion llanw yn symud gyda’r llanw ac nid oes ganddynt ystod arferol."),
    ("Bars cannot be compared between gauges.", "Ni ellir cymharu bariau rhwng medryddion."),
    ("{Q} · # km", "{Q} · # km"), ("{P} · # km", "{P} · # km"),
    ("tidal gauge, no usual range", "medrydd llanw, dim ystod arferol"),
    ("no usual range published", "dim ystod arferol wedi’i chyhoeddi"),
    ("below", "islaw"), ("usual", "arferol"), ("above", "uwchlaw"),
    ("rising", "yn codi"), ("falling", "yn gostwng"), ("steady", "yn sefydlog"),
    ("River gauges against their usual ranges", "Medryddion afonydd o’u cymharu â’u hystodau arferol"),
    ("Latest readings from Natural Resources Wales river level stations (Open Government Licence v#), with NRW's own rising, steady or falling trend.",
     "Y darlleniadau diweddaraf o orsafoedd lefel afonydd Cyfoeth Naturiol Cymru (Trwydded Llywodraeth Agored v#), gyda thuedd CNC ei hun: codi, sefydlog neu ostwng."),
    ("Each station reports on its own scale in metres, so levels cannot be compared between stations.",
     "Mae pob gorsaf yn adrodd ar ei graddfa ei hun mewn metrau, felly ni ellir cymharu lefelau rhwng gorsafoedd."),
    ("The usual range (shaded band, where known) is the range the level is in #% of the time, as published by RiverLevels.uk from NRW data.",
     "Yr ystod arferol (y llain gysgodol, lle mae’n hysbys) yw’r ystod y mae’r lefel ynddi #% o’r amser, fel y’i cyhoeddir gan RiverLevels.uk o ddata CNC."),
    ("The line builds up from the readings collected each time this page is refreshed.", "Mae’r llinell yn tyfu o’r darlleniadau a gesglir bob tro y caiff y dudalen hon ei hadnewyddu."),
    ("The {P}, Dulais, {P} and Afan rise quickly after {X} on the hills above the valleys.",
     "Mae afonydd{Px} Nedd, Dulais,{Px} Tawe ac Afan yn codi’n gyflym ar ôl {X} ar y bryniau uwchben y cymoedd."),
    ("This is a level reading, not a flood forecast.", "Darlleniad lefel yw hwn, nid rhagolwg llifogydd."),
    ("Check", "Gwiriwch"),
    ("Below usual range", "Islaw’r ystod arferol"), ("Above usual range", "Uwchlaw’r ystod arferol"), ("Within usual range", "O fewn yr ystod arferol"),
    ("Usual range not published", "Ystod arferol heb ei chyhoeddi"),
    ("{Q}, latest reading", "{Q}, darlleniad diweddaraf"),
]:
    add(en, cy)
for w_en, w_cy in [("within", "o fewn yr"), ("below", "islaw’r"), ("above", "uwchlaw’r")]:
    add(f"{{Q}}, {w_en} usual range", f"{{Q}}, {w_cy} ystod arferol")
for t_en, t_cy in TREND:
    add(f"{{Q}}, level {t_en}", f"{{Q}}, lefel {t_cy}")
    add(f"Its level is {t_en}, according to NRW's trend.", f"Mae ei lefel {t_cy}, yn ôl tuedd CNC.")
    add(f"Its level is {t_en}.", f"Mae ei lefel {t_cy}.")
for p_en, p_cy in POS:
    for r_en, r_cy in READ:
        add(f", {p_en} of # to # m{r_en}.", f", {p_cy} o # i # m{r_cy}.")
    for t_en, t_cy in TREND + [("", "")]:
        add(f"{{Q}}: # metres, {p_en} (# to # metres)" + (f", {t_en}" if t_en else ""),
            f"{{Q}}: # metr, {p_cy} (# i # metr)" + (f", {t_cy}" if t_cy else ""))
for t_en, t_cy in TREND + [("", "")]:
    tt_en, tt_cy = (f", {t_en}", f", {t_cy}") if t_en else ("", "")
    add("{Q}: # metres, a tidal gauge, so it moves with the tide" + tt_en, "{Q}: # metr, medrydd llanw, felly mae’n symud gyda’r llanw" + tt_cy)
    add("{Q}: # metres, no usual range published" + tt_en, "{Q}: # metr, dim ystod arferol wedi’i chyhoeddi" + tt_cy)
for r_en, r_cy in READ:
    add(f"It is a tidal gauge, so its level moves with the tide and it has no usual range{r_en}.",
        f"Medrydd llanw yw hwn, felly mae ei lefel yn symud gyda’r llanw ac nid oes ganddo ystod arferol{r_cy}.")
    add(f"No usual range is published for it{r_en}.", f"Nid oes ystod arferol wedi’i chyhoeddi ar ei gyfer{r_cy}.")
# the summary sentences after the nearest gauge
NAMES = [("{L}", "{L}"), ("{L} and # more", "{L} a # arall")]  # one name is looked up as a one-name list
add("That is the only gauge with a published usual range is within it.", "Dyma’r unig fedrydd sydd ag ystod arferol gyhoeddedig, ac mae o fewn yr ystod.")
add("All # gauges with a published usual range are within it.", "Mae pob un o’r # medrydd sydd ag ystod arferol gyhoeddedig o fewn yr ystod.")
lead_en, lead_cy = "Of the # gauges with a published usual range, # are within it", "O’r # medrydd sydd ag ystod arferol gyhoeddedig, mae # o fewn yr ystod"
for n_en, n_cy in NAMES:
    hi_en, hi_cy = f", # are above it ({n_en})", f", mae # uwchlaw’r ystod ({n_cy})"
    lo_en, lo_cy = f", # are below it ({n_en})", f", mae # islaw’r ystod ({n_cy})"
    add(lead_en + hi_en + ".", lead_cy + hi_cy + ".")
    add(lead_en + lo_en + ".", lead_cy + lo_cy + ".")
    for n2_en, n2_cy in NAMES:
        add(lead_en + hi_en + f", # are below it ({n2_en}).", lead_cy + hi_cy + f", mae # islaw’r ystod ({n2_cy}).")
for n_en, n_cy in NAMES:
    add(f"# gauges are rising: {n_en}.", f"Mae # medrydd yn codi: {n_cy}.")
add("# other readings are more than # hours old.", "Mae # darlleniad arall yn hŷn na # awr.")

# ---------------------------------------------------------------- floods (NPT)
SEV = [("flood alert", "flooding is possible, so be prepared", "hysbysiad llifogydd", "mae llifogydd yn bosibl, felly byddwch yn barod"),
       ("flood warning", "flooding is expected, so act now", "rhybudd llifogydd", "disgwylir llifogydd, felly gweithredwch nawr"),
       ("severe flood warning", "danger to life", "rhybudd llifogydd difrifol", "perygl i fywyd")]
for en, cy in [
    ("Flood warning data is not available at the moment, so nothing can be said about {P}.", "Nid yw data rhybuddion llifogydd ar gael ar hyn o bryd, felly ni ellir dweud dim am {P}."),
    ("Check Natural Resources Wales.", "Gwiriwch wefan Cyfoeth Naturiol Cymru."),
    ("Please check Natural Resources Wales.", "Gwiriwch wefan Cyfoeth Naturiol Cymru."),
    ("Nothing is in force: Natural Resources Wales has no flood alerts or warnings for {P}, checked #:#.",
     "Does dim mewn grym: nid oes gan Gyfoeth Naturiol Cymru unrhyw hysbysiadau na rhybuddion llifogydd ar gyfer {P}, gwiriwyd am #:#."),
    ("Flood data is out of date or missing, so no level can be shown", "Mae’r data llifogydd wedi dyddio neu ar goll, felly ni ellir dangos lefel"),
    ("Flood level ladder: none, alert, warning, severe.", "Ysgol lefel llifogydd: dim, hysbysiad, rhybudd, difrifol."),
    ("None", "Dim"), ("Alert", "Hysbysiad"), ("Warning", "Rhybudd"), ("Severe", "Difrifol"),
    ("What the Wales outlook tells us", "Beth mae rhagolwg Cymru yn ei ddweud wrthym"),
    ("Natural Resources Wales' flood outlook says: “", "Mae rhagolwg llifogydd Cyfoeth Naturiol Cymru yn dweud: “"),
    ("Natural Resources Wales' flood outlook, issued {D}, says: “", "Mae rhagolwg llifogydd Cyfoeth Naturiol Cymru, a gyhoeddwyd {D}, yn dweud: “"),
    ("” This page could not read a level from that wording, so no step is highlighted.", "” Ni allai’r dudalen hon ddarllen lefel o’r geiriad hwnnw, felly nid oes cam wedi’i amlygu."),
    ("” That is", "” Mae hynny’n"),
    ("on NRW's four-step scale (very low, low, medium, high).", "ar raddfa pedwar cam CNC (isel iawn, isel, canolig, uchel)."),
    ("very low", "isel iawn"), ("low", "isel"), ("medium", "canolig"), ("high", "uchel"),
    ("Very low", "Isel iawn"),
    ("It covers Wales as a whole, not {P} alone.", "Mae’n cwmpasu Cymru gyfan, nid {P} yn unig."),
    ("Wales flood outlook: level not stated in the text", "Rhagolwg llifogydd Cymru: nid yw’r lefel wedi’i nodi yn y testun"),
    ("Wales flood outlook scale: very low, low, medium, high.", "Graddfa rhagolwg llifogydd Cymru: isel iawn, isel, canolig, uchel."),
    ("No flood warnings or alerts in force in {P}.", "Dim rhybuddion na hysbysiadau llifogydd mewn grym yn {P}."),
    ("Flood alerts and warnings in force in {P}:", "Hysbysiadau a rhybuddion llifogydd mewn grym yn {P}:"),
    ("Flood warning data is not available at the moment.", "Nid yw data rhybuddion llifogydd ar gael ar hyn o bryd."),
    ("Natural Resources Wales, checked {D}.", "Cyfoeth Naturiol Cymru, gwiriwyd {D}."),
    ("Natural Resources Wales, checked {D} and now out of date, so check NRW.", "Cyfoeth Naturiol Cymru, gwiriwyd {D}, ac mae bellach wedi dyddio, felly gwiriwch wefan CNC."),
    ("Flood outlook (NRW, issued {D}):", "Rhagolwg llifogydd (CNC, cyhoeddwyd {D}):"),
    ("Flood outlook (NRW, issued date unknown):", "Rhagolwg llifogydd (CNC, dyddiad cyhoeddi anhysbys):"),
    ("Not an official warning service.", "Nid gwasanaeth rhybuddio swyddogol yw hwn."),
    ("For flood warnings check", "Am rybuddion llifogydd, gwiriwch"),
    ("Natural Resources Wales", "Cyfoeth Naturiol Cymru"),
    ("or call Floodline # # #.", "neu ffoniwch Floodline ar # # #."),
    ("Contains Natural Resources Wales information © Natural Resources Wales and Database Right.",
     "Yn cynnwys gwybodaeth Cyfoeth Naturiol Cymru © Cyfoeth Naturiol Cymru a Hawl Cronfa Ddata."),
    ("All rights Reserved.", "Cedwir pob hawl."),
    ("Flood alerts and warnings published by Natural Resources Wales for the rivers and coast of {P}.",
     "Hysbysiadau a rhybuddion llifogydd a gyhoeddir gan Gyfoeth Naturiol Cymru ar gyfer afonydd ac arfordir {P}."),
    ("Alerts and warnings change quickly, so check", "Mae hysbysiadau a rhybuddion yn newid yn gyflym, felly gwiriwch"),
    ("Natural Resources Wales flood alerts and warnings in force (#)", "Hysbysiadau a rhybuddion llifogydd Cyfoeth Naturiol Cymru mewn grym (#)"),
    ("Natural Resources Wales flood warning in force", "Rhybudd llifogydd Cyfoeth Naturiol Cymru mewn grym"),
    ("Natural Resources Wales flood alert in force", "Hysbysiad llifogydd Cyfoeth Naturiol Cymru mewn grym"),
    ("Severe Flood Warning", "Rhybudd Llifogydd Difrifol"), ("Flood Warning", "Rhybudd Llifogydd"), ("Flood Alert", "Hysbysiad Llifogydd"),
]:
    add(en, cy)
for h_en, h_cy in [("# hours", "# awr")]:
    add(f"The flood data is {h_en} old, so this page cannot say whether anything is in force.",
        f"Mae’r data llifogydd yn {h_cy} oed, felly ni all y dudalen hon ddweud a oes unrhyw beth mewn grym.")
for ago_en, ago_cy in [("# days ago", "# diwrnod yn ôl"), ("# hours ago", "# awr yn ôl")]:
    add(f"Natural Resources Wales' flood outlook, issued {{D}} ({ago_en}, so it may be out of date), says: “",
        f"Mae rhagolwg llifogydd Cyfoeth Naturiol Cymru, a gyhoeddwyd {{D}} ({ago_cy}, felly gall fod wedi dyddio), yn dweud: “")
for lv_en, lv_cy in [("very low", "isel iawn"), ("low", "isel"), ("medium", "canolig"), ("high", "uchel")]:
    add(f"Current outlook: {lv_en}", f"Rhagolwg presennol: {lv_cy}")
for lv_en, lv_cy in [("none", "dim"), ("alert", "hysbysiad"), ("warning", "rhybudd"), ("severe", "difrifol")]:
    add(f"Current level for {{P}}: {lv_en}", f"Y lefel bresennol ar gyfer {{P}}: {lv_cy}")
for name, mean, name_cy, mean_cy in SEV:
    for cnt_en in ("There are # flood notices",):
        for n_en, n_cy in NAMES[:1] + [("{L}; and # more", "{L}; a # arall")]:
            add(f"{cnt_en} in force in {{P}}, the most serious being a {name} ({mean}): {n_en}.",
                f"Mae # neges llifogydd mewn grym yn {{P}}, a’r fwyaf difrifol yw {name_cy} ({mean_cy}): {n_cy}.")

# ---------------------------------------------------------------- walks (notes only: walk descriptions stay English for now)
for en, cy in [
    ("Walking weather today in {P}:", "Tywydd cerdded heddiw yn {P}:"),
    ("(rain chance #%, gusts up to # km/h from now to the end of today).", "(siawns o law #%, hyrddiau hyd at # km/a o nawr tan ddiwedd y dydd)."),
    ("(rain chance #%, gusts up to # km/h).", "(siawns o law #%, hyrddiau hyd at # km/a)."),
    ("Good news for a long one.", "Newyddion da i daith hir."),
    ("The next day rated Good is {D}.", "Y diwrnod nesaf â sgôr Da yw {D}."),
    ("No day in the forecast is rated Good yet.", "Nid oes diwrnod â sgôr Da yn y rhagolwg eto."),
    ("Walking-weather figures are not available right now.", "Nid yw ffigurau tywydd cerdded ar gael ar hyn o bryd."),
    ("Walks are listed by distance from the place you have chosen, nearest first.", "Rhestrir y teithiau cerdded yn ôl eu pellter o’r lle a ddewiswyd gennych, yr agosaf yn gyntaf."),
    ("Distances and times are approximate, and the links go to other websites whose routes may differ a little from the ones described here.",
     "Bras yw’r pellteroedd a’r amseroedd, ac mae’r dolenni’n mynd i wefannau eraill y gall eu llwybrau fod ychydig yn wahanol i’r rhai a ddisgrifir yma."),
    ('Times marked "estimate" are worked out from the distance because the source gives none, and "Not graded" means the source gives no difficulty.',
     'Mae amseroedd wedi’u marcio’n "estimate" wedi’u cyfrifo o’r pellter am nad yw’r ffynhonnell yn rhoi un, ac mae "Not graded" yn golygu nad yw’r ffynhonnell yn rhoi lefel anhawster.'),
    ("for bus and train times before setting off.", "am amseroedd bysiau a threnau cyn cychwyn."),
    ("{P} Country Park's paths, apart from public rights of way, are permissive and the park may close them from time to time.",
     "Llwybrau caniataol yw llwybrau Parc Gwledig {P}, ar wahân i hawliau tramwy cyhoeddus, a gall y parc eu cau o bryd i’w gilydd."),
    ("The small tiles beside each walk are simple illustrations of its type (waterside or fields and hills), not photographs of the route.",
     "Darluniau syml o fath y daith yw’r teils bach wrth bob taith (glan dŵr neu gaeau a bryniau), nid ffotograffau o’r llwybr."),
    ("Sources:", "Ffynonellau:"), ("Active Traveller", "Active Traveller"), ("AllTrails", "AllTrails"),
    ("Many more routes, with maps and reviews, are on", "Mae llawer mwy o lwybrau, gyda mapiau ac adolygiadau, ar"),
    ("Prefer to walk with others?", "Gwell gennych gerdded gydag eraill?"),
    ("The", "Mae"), ("{P} Ramblers", "Ramblers {P}"),
    ("lead regular group walks; their programme is on the", "yn arwain teithiau cerdded grŵp rheolaidd; mae eu rhaglen ar"),
    ("group's website", "wefan y grŵp"),
    ("About # km {X} of {P}.", "Tua # km i’r {X} o {P}."),
    ("Overall:", "At ei gilydd:"),
]:
    add(en, cy)

# ---------------------------------------------------------------- photo captions (NPT)
for en, cy in [
    ("{P} Abbey.", "Abaty Nedd{Px}."), ("{P} Abbey", "Abaty Nedd{Px}"),
    ("{P} beach.", "Traeth {P}."), ("{P} beach", "Traeth {P}"),
    ("{P} Arts Centre.", "Canolfan Gelfyddydau {P}."), ("{P} Arts Centre", "Canolfan Gelfyddydau {P}"),
    ("{P} Aqueduct, {Q}.", "Traphont Ddŵr {P}, {Q}."), ("{P} Aqueduct, {Q}", "Traphont Ddŵr {P}, {Q}"),
    ("Geograph via Wikimedia Commons", "Geograph drwy Wikimedia Commons"),
] + [(f"Photo: {n},", f"Llun: {n},") for n in ("Philip Halling", "Helen", "Chris Andrews", "M J Roscoe")]:
    add(en, cy)

# ---------------------------------------------------------------- data age lines (both boards)
DAYS = [("Mon", "Llun"), ("Tue", "Maw"), ("Wed", "Mer"), ("Thu", "Iau"), ("Fri", "Gwe"), ("Sat", "Sad"), ("Sun", "Sul")]
for d_en, d_cy in DAYS:
    add(f"Latest hourly reading: {d_en} #:# UK time", f"Darlleniad diweddaraf yr awr: {d_cy} #:# amser y DU", both=True)
    add(f"Latest hourly reading: {d_en} #:# UK time.", f"Darlleniad diweddaraf yr awr: {d_cy} #:# amser y DU.", both=True)
add("and is now # days old, so check the live sources", "ac mae bellach yn # diwrnod oed, felly gwiriwch y ffynonellau byw", both=True)


# ---------------------------------------------------------------- found with the browser clock set to the data's own time (27 Nov)
for en, cy in [
    ("Values in µg/m³, nearest station first.", "Gwerthoedd mewn µg/m³, yr orsaf agosaf yn gyntaf."),
    ("(Natural Resources Wales, checked {D}).", "(Cyfoeth Naturiol Cymru, gwiriwyd {D})."),
    # Ammanford's overflow note, sentence by sentence, in the Welsh its dictionary already uses for the whole paragraph
    ("Overflows listed: # within # km of {P} (out of # in this dashboard's area in Dŵr Cymru Welsh Water's near-real-time storm overflow map, which may not include every overflow).",
     "Gorlifoedd a restrir: # o fewn # km i {Pm} (allan o # yn ardal y dangosfwrdd hwn ar fap gorlifoedd storm bron amser real Dŵr Cymru Welsh Water, nad yw efallai’n cynnwys pob gorlif)."),
    ("This list was last refreshed {D}.", "Cafodd y rhestr hon ei hadnewyddu ddiwethaf {D}."),
    ("Data from the", "Data o"),
    ("NOW", "NAWR"),
] + [(f"▶ {en}", f"▶ {cy}") for en, cy in [("None", "Dim"), ("Alert", "Hysbysiad"), ("Severe", "Difrifol"), ("Low", "Isel"), ("High", "Uchel"), ("Medium", "Canolig")]]:
    add(en, cy)



# ---------------------------------------------------------------- lines Ammanford's page shows too
for en, cy in [
    ("Feels #° · humidity #% · dew point #° · cloud #% · UV # · visibility # km", "Teimlo fel #° · lleithder #% · gwlithbwynt #° · cwmwl #% · UV # · gwelededd # km"),
    ("#:#:# GMT", "#:#:# GMT"), ("#:#:# BST", "#:#:# BST"), ("#mm", "#mm"), ("Location", "Lleoliad"), ("{Q}", "{Q}"),
    ("Values in µg/m³, nearest station first.", "Gwerthoedd mewn µg/m³, yr orsaf agosaf yn gyntaf."),
    ("(Natural Resources Wales, checked {D}).", "(Cyfoeth Naturiol Cymru, gwiriwyd {D})."),
    ("Overflows listed: # within # km of {P} (out of # in this dashboard's area in Dŵr Cymru Welsh Water's near-real-time storm overflow map, which may not include every overflow).",
     "Gorlifoedd a restrir: # o fewn # km i {Pm} (allan o # yn ardal y dangosfwrdd hwn ar fap gorlifoedd storm bron amser real Dŵr Cymru Welsh Water, nad yw efallai’n cynnwys pob gorlif)."),
    ("This list was last refreshed {D}.", "Cafodd y rhestr hon ei hadnewyddu ddiwethaf {D}."),
    ("Data from the", "Data o"),
]:
    D.pop(en, None)
    add(en, cy, both=True)

# ---------------------------------------------------------------- age badge (28 Nov 2026), both boards
# "# hour" and "# day" are looked up as the plural keys (agree() in parts/cy.js)
for en, cy in [('Updated just now', 'Newydd ei ddiweddaru'), ('Updated # min ago', 'Diweddarwyd # munud yn ôl'), ('Updated # hours ago', 'Diweddarwyd # awr yn ôl'), ('Updated # days ago', 'Diweddarwyd # diwrnod yn ôl'), ('Old data · Updated # hours ago', 'Hen ddata · Diweddarwyd # awr yn ôl'), ('Old data · Updated # days ago', 'Hen ddata · Diweddarwyd # diwrnod yn ôl')]:
    add(en, cy, both=True)

def main(argv):
    cur = json.load(open(argv[1], encoding="utf-8"))
    if "all" not in cur:  # the first, flat file: the template's own lines (verdict, credits)
        cur = {"all": cur, "neath-port-talbot": {}}
    amm = json.load(open(argv[2], encoding="utf-8"))
    out = {"all": dict(cur["all"]), "neath-port-talbot": dict(cur.get("neath-port-talbot", {}))}
    skipped = []
    for k, v in D.items():
        if k in amm:
            skipped.append(k)
            continue
        out["all" if k in BOTH else "neath-port-talbot"][k] = v
    for k in out["all"]:
        out["neath-port-talbot"].pop(k, None)
    for sec in out.values():
        for k, v in sec.items():
            for slot in ("{D}", "{X}", "{Q}", "{L}", "#"):
                if k.count(slot) != v.count(slot):
                    raise SystemExit(f"{slot} count differs: {k!r} -> {v!r}")
            if k.count("{P}") != sum(v.count(s) for s in ("{P}", "{Pm}", "{Pe}", "{Px}")):
                raise SystemExit(f"place count differs: {k!r} -> {v!r}")
    out = {"about": "Welsh both Welsh weather boards add to their CYW dictionary: \"all\" for both, "
                    "\"neath-port-talbot\" for lines only that board shows (Ammanford's own chart code writes "
                    "its Welsh). Made by tools/make_cy_shared.py. Drafts, not checked by a Welsh speaker.", **out}
    json.dump(out, open(argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(argv[3], "a", encoding="utf-8").write("\n")
    print(f"all: {len(out['all'])} lines, neath-port-talbot: {len(out['neath-port-talbot'])} lines; "
          f"{len(skipped)} left to Ammanford's own dictionary")
    for k in skipped:
        print("  already in Ammanford's W:", k)


if __name__ == "__main__":
    main(sys.argv)
