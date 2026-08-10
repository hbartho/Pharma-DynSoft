# -*- coding: utf-8 -*-
"""Génère le manuel d'utilisation PDF de DynPharma."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak, KeepTogether)
from PIL import Image as PILImage

SCREENS = "/app/backend/static/manual_screens"
OUT = "/app/backend/static/manuel_utilisation_dynpharma.pdf"

TEAL = HexColor("#0d9488")
DARK = HexColor("#0f172a")
SLATE = HexColor("#475569")
LIGHT_BG = HexColor("#f0fdfa")
BORDER = HexColor("#99f6e4")
ORANGE = HexColor("#c2410c")
ORANGE_BG = HexColor("#fff7ed")

styles = getSampleStyleSheet()
st_title = ParagraphStyle('T', parent=styles['Title'], fontSize=30, textColor=DARK, spaceAfter=6)
st_subtitle = ParagraphStyle('ST', parent=styles['Normal'], fontSize=14, textColor=TEAL, alignment=TA_CENTER)
st_h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, textColor=TEAL, spaceBefore=18, spaceAfter=8)
st_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13.5, textColor=DARK, spaceBefore=12, spaceAfter=5)
st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, textColor=SLATE, leading=15, spaceAfter=5)
st_step = ParagraphStyle('S', parent=st_body, leftIndent=16, bulletIndent=4, spaceAfter=3)
st_note = ParagraphStyle('N', parent=st_body, textColor=ORANGE, backColor=ORANGE_BG, borderPadding=7,
                         borderColor=HexColor("#fdba74"), borderWidth=0.7, borderRadius=4, leftIndent=4, spaceBefore=6, spaceAfter=8)
st_tip = ParagraphStyle('TIP', parent=st_body, textColor=HexColor("#0f766e"), backColor=LIGHT_BG, borderPadding=7,
                        borderColor=BORDER, borderWidth=0.7, borderRadius=4, leftIndent=4, spaceBefore=6, spaceAfter=8)
st_caption = ParagraphStyle('C', parent=st_body, fontSize=8.5, alignment=TA_CENTER, textColor=SLATE, spaceBefore=3, spaceAfter=10)
st_toc = ParagraphStyle('TOC', parent=st_body, fontSize=11, leading=20)

story = []

def h1(t): story.append(Paragraph(t, st_h1))
def h2(t): story.append(Paragraph(t, st_h2))
def p(t): story.append(Paragraph(t, st_body))
def steps(items):
    for i, s in enumerate(items, 1):
        story.append(Paragraph(f"<b>{i}.</b> {s}", st_step))
    story.append(Spacer(1, 4))
def bullets(items):
    for s in items:
        story.append(Paragraph(f"• {s}", st_step))
    story.append(Spacer(1, 4))
def note(t): story.append(Paragraph(f"<b>⚠ Important :</b> {t}", st_note))
def tip(t): story.append(Paragraph(f"<b>💡 Astuce :</b> {t}", st_tip))

def screen(name, caption):
    path = os.path.join(SCREENS, f"{name}.png")
    if not os.path.exists(path):
        return
    img = PILImage.open(path)
    w, h = img.size
    max_w = 16.5 * cm
    max_h = 10.5 * cm
    ratio = min(max_w / w, max_h / h)
    el = Image(path, width=w * ratio, height=h * ratio)
    story.append(KeepTogether([Spacer(1, 6), el, Paragraph(caption, st_caption)]))

def table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('TEXTCOLOR', (0, 1), (-1, -1), SLATE),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor("#f8fafc")]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

def cell(t): return Paragraph(t, ParagraphStyle('cell', parent=st_body, fontSize=8.5, leading=11, spaceAfter=0))

# ==================== COUVERTURE ====================
story.append(Spacer(1, 5 * cm))
story.append(Paragraph("DynPharma", st_title))
story.append(Paragraph("Manuel d'utilisation complet", st_subtitle))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph("Application de gestion de pharmacie", ParagraphStyle('c1', parent=st_body, alignment=TA_CENTER, fontSize=12)))
story.append(Paragraph("Ventes • Stock • Approvisionnements • Dettes • Caisse • Rapports", ParagraphStyle('c2', parent=st_body, alignment=TA_CENTER, fontSize=10)))
story.append(Spacer(1, 8 * cm))
story.append(Paragraph("Version 1.0 — Juin 2026", ParagraphStyle('c3', parent=st_body, alignment=TA_CENTER, fontSize=9)))
story.append(PageBreak())

# ==================== SOMMAIRE ====================
h1("Sommaire")
toc = [
    "1. Présentation de l'application",
    "2. Rôles et permissions",
    "3. Connexion et premiers pas",
    "4. Tableau de bord",
    "5. Gestion de la caisse (Shifts)",
    "6. Planification des shifts (Admin)",
    "7. Effectuer une vente",
    "8. Rabais et codes promo",
    "9. Ventes en attente",
    "10. Retours de produits",
    "11. Gestion des produits",
    "12. Approvisionnements (achats fournisseurs)",
    "13. Gestion du stock (mouvements, pertes, inventaire)",
    "14. Clients et dettes clients",
    "15. Fournisseurs et solde fournisseurs (dettes / avoirs)",
    "16. Ordonnances",
    "17. Rapports et statistiques",
    "18. Utilisateurs (Admin)",
    "19. Paramètres",
    "20. Mode hors-ligne (PWA)",
    "21. Questions fréquentes (FAQ)",
    "22. Glossaire",
]
for t in toc:
    story.append(Paragraph(t, st_toc))
story.append(PageBreak())

# ==================== 1. PRESENTATION ====================
h1("1. Présentation de l'application")
p("<b>DynPharma</b> est une application complète de gestion de pharmacie. Elle fonctionne sur ordinateur, "
  "tablette et téléphone (application web progressive — PWA) et continue de fonctionner même sans connexion internet.")
p("Elle couvre l'ensemble du cycle de travail d'une pharmacie :")
bullets([
    "<b>Ventes</b> : caisse tactile, plusieurs modes de paiement, rabais, ventes à crédit",
    "<b>Stock</b> : produits, lots, alertes de stock bas et de péremption, inventaire physique",
    "<b>Approvisionnements</b> : achats fournisseurs, calcul automatique des prix de vente",
    "<b>Finances</b> : dettes clients, solde fournisseurs (dettes et avoirs), rapports",
    "<b>Équipe</b> : gestion des utilisateurs, shifts de caisse, planification des horaires",
])
h2("Règles de calcul des prix")
p("L'application applique des règles de prix strictes :")
bullets([
    "<b>Prix de cession (HT)</b> : c'est le prix d'achat auprès du fournisseur. Tous les totaux d'approvisionnement sont calculés sur ce prix.",
    "<b>Prix public</b> : c'est le prix de vente au client. Il est calculé automatiquement : <b>Prix public = Prix de cession × Coefficient de marge</b> (par défaut 1,4).",
    "Le coefficient de marge est défini par catégorie de produit et peut être modifié par l'administrateur.",
])
p("La devise utilisée est le <b>Franc Guinéen (GNF)</b>, modifiable dans les Paramètres.")

# ==================== 2. ROLES ====================
h1("2. Rôles et permissions")
p("Chaque utilisateur possède un rôle qui détermine ce qu'il peut faire dans l'application :")
table([
    [cell("<b>Fonctionnalité</b>"), cell("<b>Admin</b>"), cell("<b>Pharmacien</b>"), cell("<b>Caissier</b>")],
    [cell("Tableau de bord"), cell("✓"), cell("✓"), cell("✓")],
    [cell("Ventes / Caisse"), cell("✓"), cell("✓"), cell("✓")],
    [cell("Produits (création / modification)"), cell("✓"), cell("✓"), cell("—")],
    [cell("Approvisionnements"), cell("✓"), cell("✓"), cell("✓ (saisie)")],
    [cell("Validation des approvisionnements"), cell("✓"), cell("✓"), cell("—")],
    [cell("Clients et dettes clients"), cell("✓"), cell("✓"), cell("✓")],
    [cell("Fournisseurs"), cell("✓"), cell("✓"), cell("—")],
    [cell("Solde fournisseurs (dettes / avoirs)"), cell("✓"), cell("—"), cell("—")],
    [cell("Codes promo et règles de rabais"), cell("✓"), cell("—"), cell("—")],
    [cell("Planification des shifts"), cell("✓"), cell("—"), cell("—")],
    [cell("Rapports"), cell("✓"), cell("✓"), cell("—")],
    [cell("Utilisateurs"), cell("✓"), cell("—"), cell("—")],
    [cell("Paramètres"), cell("✓"), cell("—"), cell("—")],
    [cell("Création de comptes utilisateurs"), cell("✓"), cell("—"), cell("—")],
], col_widths=[7.5 * cm, 3 * cm, 3 * cm, 3 * cm])
note("Les caissiers et pharmaciens ne peuvent travailler que pendant leurs horaires planifiés. "
     "En dehors de ces horaires, certaines pages affichent « Accès restreint — Hors horaires de travail ». "
     "L'administrateur n'a aucune restriction.")

# ==================== 3. CONNEXION ====================
h1("3. Connexion et premiers pas")
steps([
    "Ouvrez l'application dans votre navigateur (Chrome recommandé).",
    "Saisissez votre <b>adresse e-mail</b> et votre <b>mot de passe</b> fournis par l'administrateur.",
    "Cliquez sur <b>Se connecter</b>.",
    "Vous arrivez sur le <b>Tableau de bord</b>.",
])
screen("login", "Écran de connexion DynPharma")
tip("Sur téléphone ou tablette, vous pouvez installer l'application : ouvrez le menu du navigateur puis "
    "« Ajouter à l'écran d'accueil ». L'application s'ouvrira alors comme une application mobile classique.")
note("Seul l'administrateur peut créer de nouveaux comptes utilisateurs (voir chapitre 18).")
h2("Navigation")
bullets([
    "Sur <b>ordinateur</b> : le menu principal se trouve dans la barre latérale gauche.",
    "Sur <b>mobile</b> : appuyez sur le bouton ☰ (hamburger) en haut à gauche pour ouvrir le menu.",
    "L'indicateur de <b>shift en cours</b> et l'état de <b>synchronisation</b> sont toujours visibles.",
])

# ==================== 4. DASHBOARD ====================
h1("4. Tableau de bord")
p("Le tableau de bord donne une vue d'ensemble en temps réel de l'activité de la pharmacie.")
screen("dashboard", "Tableau de bord avec statistiques du jour")
h2("Informations affichées")
bullets([
    "<b>Ventes du jour</b> : montant total et nombre de transactions",
    "<b>Ventes par mode de paiement</b> : Espèces, Carte, Orange Money, MTN Money, Chèque — avec le détail des rabais accordés et des ventes partielles (crédit)",
    "<b>Retours aujourd'hui</b> : nombre et montant des retours de produits du jour",
    "<b>Produits en péremption</b> : badge d'alerte pour les produits qui expirent bientôt — cliquez dessus pour voir la liste filtrée",
    "<b>Alertes stock bas</b> : produits sous le seuil minimum",
    "<b>Graphique des 7 derniers jours</b> : évolution des ventes",
])
tip("Cliquez sur le badge « Produits en péremption » pour ouvrir directement la page Produits filtrée sur les produits périmés ou proches de la péremption.")

# ==================== 5. SHIFTS ====================
h1("5. Gestion de la caisse (Shifts)")
p("Avant de pouvoir vendre, chaque caissier ou pharmacien doit <b>ouvrir un shift</b> (session de caisse). "
  "À la fin de son service, il doit <b>fermer son shift</b> en comptant la caisse.")
screen("shifts", "Page de gestion des shifts")
h2("Ouvrir un shift")
steps([
    "Allez dans le menu <b>Shifts</b> (ou cliquez sur l'indicateur de shift).",
    "Cliquez sur <b>Ouvrir le shift</b>.",
    "Saisissez le <b>fonds de caisse initial</b> (montant en espèces présent dans la caisse au démarrage).",
    "Vérifiez l'heure de fin prévue (pré-remplie depuis la planification).",
    "Confirmez. Vous pouvez maintenant effectuer des ventes.",
])
note("Un caissier ou pharmacien ne peut ouvrir un shift que s'il a été <b>planifié</b> par l'administrateur pour ce jour, "
     "et uniquement pendant ses horaires. Sinon le bouton est grisé avec le message « Non planifié aujourd'hui » ou « Hors horaires de travail ».")
h2("Fermer un shift")
steps([
    "Comptez l'argent réellement présent dans la caisse.",
    "Cliquez sur <b>Fermer le shift</b>.",
    "Saisissez le <b>montant compté</b>.",
    "L'application compare avec le montant théorique et enregistre l'écart éventuel.",
    "Confirmez la fermeture.",
])
note("Le « montant attendu » n'est visible que par l'administrateur, afin de garantir un comptage honnête de la caisse.")
h2("Historique des shifts")
p("La page <b>Historique des shifts</b> liste tous les shifts passés avec : agent, heures d'ouverture/fermeture, "
  "fonds initial, montant compté et écart de caisse.")

# ==================== 6. PLANIFICATION ====================
h1("6. Planification des shifts (Admin)")
p("L'administrateur planifie les horaires de travail de chaque employé dans un calendrier.")
screen("planification", "Calendrier de planification des shifts")
h2("Créer une planification")
steps([
    "Menu <b>Planification</b> → choisissez la vue <b>Mois</b> ou <b>Semaine</b>.",
    "Cliquez sur un jour du calendrier.",
    "Sélectionnez l'<b>employé</b>, l'<b>heure de début</b>, l'<b>heure de fin</b> et la durée maximale.",
    "Ajoutez une note si nécessaire, puis enregistrez.",
])
tip("Utilisez la <b>planification rapide</b> pour créer plusieurs planifications d'un coup (par exemple toute une semaine).")
bullets([
    "Un employé <b>non planifié</b> ne peut pas ouvrir de shift ce jour-là.",
    "Un employé ne peut pas ouvrir de shift <b>avant l'heure de début</b> ni <b>après l'heure de fin</b>.",
    "Les planifications peuvent être modifiées ou supprimées à tout moment.",
])

# ==================== 7. VENTES ====================
h1("7. Effectuer une vente")
p("La page <b>Ventes</b> est le cœur de l'application : c'est ici que vous encaissez les clients.")
screen("ventes", "Page des ventes avec historique")
h2("Créer une nouvelle vente")
steps([
    "Menu <b>Ventes</b> → cliquez sur <b>Nouvelle vente</b>.",
    "Recherchez un produit par son nom et cliquez dessus pour l'ajouter au panier.",
    "Ajustez les <b>quantités</b> si besoin. Le total se calcule automatiquement (prix public).",
    "Sélectionnez éventuellement un <b>client</b> (obligatoire pour une vente à crédit).",
    "Appliquez un rabais ou un code promo si nécessaire (voir chapitre 8).",
    "Choisissez le <b>mode de paiement</b> et saisissez le montant reçu.",
    "Validez la vente. Le stock est automatiquement diminué et le reçu peut être imprimé.",
])
h2("Modes de paiement disponibles")
table([
    [cell("<b>Mode</b>"), cell("<b>Fonctionnement</b>")],
    [cell("Espèces"), cell("Paiement en liquide. La monnaie à rendre est calculée automatiquement.")],
    [cell("Carte bancaire"), cell("Paiement par TPE.")],
    [cell("Orange Money"), cell("Saisir le n° du destinataire et la référence du paiement marchand, puis vérification OTP.")],
    [cell("MTN Money"), cell("Même principe qu'Orange Money.")],
    [cell("Chèque"), cell("Paiement par chèque.")],
    [cell("Crédit (dette)"), cell("Le client paye plus tard. Un client doit être sélectionné et son plafond de dette est vérifié.")],
    [cell("Paiement mixte"), cell("Combinaison de plusieurs modes (ex. : une partie en espèces + une partie en Orange Money, ou partiel + crédit).")],
], col_widths=[4 * cm, 12.5 * cm])
h2("Vente à crédit (dette client)")
bullets([
    "Sélectionnez le client, puis choisissez <b>Crédit</b> ou saisissez un paiement partiel.",
    "Le montant non payé devient une <b>dette client</b> visible dans le module Dettes.",
    "Si le client dépasse son <b>plafond de dette autorisé</b>, la vente à crédit est refusée.",
])

# ==================== 8. RABAIS ====================
h1("8. Rabais et codes promo")
p("DynPharma gère quatre types de rabais, cumulables, tous visibles dans le récapitulatif de la vente :")
table([
    [cell("<b>Type</b>"), cell("<b>Description</b>"), cell("<b>Qui le déclenche ?</b>")],
    [cell("Rabais manuel"), cell("Pourcentage ou montant fixe saisi librement sur la vente."), cell("Le vendeur")],
    [cell("Code promo"), cell("Code créé par l'admin, validé en temps réel lors de la saisie (conditions : montant min., nombre d'utilisations…)."), cell("Le client donne le code")],
    [cell("Rabais automatique"), cell("Appliqué automatiquement selon des règles : volume d'achat, fidélité du client, produits proches de la péremption."), cell("Automatique")],
    [cell("Rabais par produit"), cell("% ou montant sur une ligne précise du panier, avec motif optionnel."), cell("Le vendeur")],
], col_widths=[3.2 * cm, 9 * cm, 4.3 * cm])
h2("Règles de rabais automatiques (exemples actifs)")
bullets([
    "<b>Volume</b> : 3 % de rabais pour tout achat supérieur à 50 000 GNF",
    "<b>Fidélité</b> : 5 % pour les clients ayant effectué au moins 20 achats",
    "<b>Péremption proche</b> : 10 % pour les produits expirant dans moins de 30 jours",
])
screen("codes_promo", "Gestion des codes promo (Admin)")
h2("Créer un code promo (Admin)")
steps([
    "Menu <b>Codes Promo</b> → <b>Nouveau code</b>.",
    "Définissez le code (ex. : PROMO10), le type de remise (% ou montant) et sa valeur.",
    "Fixez les conditions : montant minimum d'achat, dates de validité, nombre maximum d'utilisations.",
    "Enregistrez. Le code est immédiatement utilisable en caisse.",
])
p("Les pages <b>Règles de Rabais</b> et <b>Historique des Rabais</b> permettent respectivement de gérer les règles "
  "automatiques et de consulter tous les rabais accordés (avec le code de l'agent qui a réalisé la vente).")

# ==================== 9. VENTES EN ATTENTE ====================
h1("9. Ventes en attente")
p("Une vente peut être mise « en pause » pour être reprise plus tard, par exemple quand un client va chercher "
  "de l'argent ou qu'un autre client est pressé.")
steps([
    "Dans le formulaire de vente, remplissez le panier puis cliquez sur <b>Mettre en attente</b>.",
    "La vente est sauvegardée sans toucher au stock.",
    "Pour la reprendre : ouvrez la modale <b>Ventes en attente</b>, puis cliquez sur <b>Reprendre</b>.",
    "Terminez la vente normalement (le stock n'est déduit qu'à la finalisation).",
])
bullets([
    "Les ventes en attente sont <b>partagées entre tous les utilisateurs</b>.",
    "Elles <b>expirent automatiquement après 24 heures</b>.",
    "Vous pouvez aussi les supprimer manuellement.",
])

# ==================== 10. RETOURS ====================
h1("10. Retours de produits")
p("Un client peut retourner un produit dans le délai autorisé (3 jours par défaut, configurable dans les Paramètres).")
steps([
    "Ouvrez l'<b>historique des ventes</b> et retrouvez la vente concernée.",
    "Cliquez sur l'action <b>Retour</b>.",
    "Sélectionnez les produits et quantités retournés, indiquez le motif.",
    "Validez : le stock est réintégré et le remboursement est enregistré.",
])
p("Les retours du jour apparaissent sur le tableau de bord (« Retours aujourd'hui ») et sont déduits des rapports de vente.")

# ==================== 11. PRODUITS ====================
h1("11. Gestion des produits")
screen("produits", "Catalogue des produits avec stock et alertes")
h2("Créer un produit")
steps([
    "Menu <b>Produits</b> → <b>Nouveau produit</b>.",
    "Renseignez le nom, la <b>catégorie</b>, l'unité, le taux de TVA.",
    "Saisissez le <b>prix de cession</b> (prix d'achat HT) : le <b>prix public</b> est calculé automatiquement (prix de cession × coefficient de la catégorie).",
    "Définissez le <b>stock minimum</b> pour recevoir des alertes de stock bas.",
    "Enregistrez.",
])
h2("Recherche et filtres")
bullets([
    "Recherche instantanée par nom.",
    "Filtres par <b>catégorie</b> et par <b>statut</b> (stock bas, rupture, périmés…).",
    "La liste se charge automatiquement en défilant (scroll infini).",
])
h2("Coefficients de marge")
p("Chaque catégorie possède un <b>coefficient de marge</b> (1,4 par défaut). Lorsqu'un approvisionnement est validé, "
  "le prix public de chaque produit est recalculé : <b>Prix public = Prix de cession × Coefficient</b>. "
  "L'administrateur peut modifier les coefficients dans la <b>Gestion des prix</b>.")

# ==================== 12. APPROVISIONNEMENTS ====================
h1("12. Approvisionnements (achats fournisseurs)")
p("Un approvisionnement enregistre une livraison de produits par un fournisseur. Il suit un cycle en deux étapes : "
  "<b>saisie</b> puis <b>validation</b>.")
screen("approvisionnements", "Liste des approvisionnements")
h2("Créer un approvisionnement")
steps([
    "Menu <b>Approvisionnements</b> → <b>Nouvel approvisionnement</b>.",
    "Sélectionnez le <b>fournisseur</b> et la date.",
    "Ajoutez chaque produit livré avec : quantité, <b>prix de cession HT</b>, n° de lot, emplacement, <b>date de péremption</b> (obligatoirement future).",
    "Vous pouvez saisir un <b>prix public modifié</b> si vous voulez remplacer le prix calculé automatiquement.",
    "Renseignez la TVA déductible le cas échéant.",
    "Enregistrez : l'approvisionnement est en statut <b>En attente</b>.",
])
h2("Valider un approvisionnement (Admin / Pharmacien)")
p("La validation est l'étape qui applique réellement la livraison :")
bullets([
    "Le <b>stock</b> de chaque produit est augmenté des quantités livrées.",
    "Le <b>prix de cession</b> (prix d'achat) du produit est mis à jour.",
    "Le <b>prix public</b> (prix de vente) est recalculé : prix de cession × coefficient de la catégorie (ou prix public modifié saisi).",
    "Une <b>dette fournisseur</b> est automatiquement créée pour le montant de la livraison.",
    "Les <b>lots</b> sont enregistrés avec leur date de péremption pour la gestion FEFO.",
])
note("Tous les totaux d'approvisionnement sont calculés sur le <b>prix de cession HT</b>. "
     "Vérifiez soigneusement les prix avant de valider : la validation met à jour les prix de vente en caisse.")

# ==================== 13. STOCK ====================
h1("13. Gestion du stock")
h2("Mouvements de stock")
screen("mouvements_stock", "Historique des mouvements de stock")
p("Chaque entrée (approvisionnement, retour) et sortie (vente, perte) est tracée avec la date, le produit, la quantité "
  "et le code de l'employé responsable.")
h2("Pertes de stock")
screen("pertes_stock", "Déclaration des pertes")
steps([
    "Menu <b>Pertes</b> → <b>Déclarer une perte</b>.",
    "Sélectionnez le produit, la quantité perdue et le motif (casse, péremption, vol…).",
    "Validez : le stock est diminué et la perte est historisée.",
])
h2("Inventaire physique")
screen("inventaire", "Inventaire physique")
steps([
    "Menu <b>Inventaire</b> → filtrez éventuellement par catégorie.",
    "Comptez physiquement chaque produit et saisissez le <b>stock réel</b>.",
    "L'application calcule automatiquement les <b>écarts</b> avec le stock théorique.",
    "Validez l'inventaire pour ajuster les stocks. La feuille d'inventaire peut être imprimée.",
])
tip("La valorisation du stock utilise la méthode <b>FEFO</b> (First Expired, First Out) : les lots qui périment "
    "en premier sortent en premier.")

# ==================== 14. CLIENTS / DETTES ====================
h1("14. Clients et dettes clients")
screen("clients", "Fiches clients")
h2("Créer un client")
steps([
    "Menu <b>Clients</b> → <b>Nouveau client</b>.",
    "Renseignez le nom, le téléphone et éventuellement un <b>plafond de dette autorisé</b>.",
    "Enregistrez. Le client peut maintenant être associé aux ventes.",
])
h2("Dettes clients")
screen("dettes", "Tableau de bord des dettes clients")
p("Le module <b>Dettes</b> centralise toutes les créances clients :")
bullets([
    "Vue d'ensemble : total dû, nombre de débiteurs, top clients endettés.",
    "<b>Encaisser un remboursement</b> : partiel ou total, avec choix du mode de paiement. Le solde se met à jour immédiatement.",
    "<b>Remboursement groupé</b> : régler plusieurs dettes d'un client en une seule opération.",
    "<b>Abandon de dette</b> : annuler une créance irrécouvrable avec justification (Admin).",
    "Les dettes anciennes (plus de 90 jours par défaut) sont marquées <b>En retard</b>.",
])

# ==================== 15. FOURNISSEURS ====================
h1("15. Fournisseurs et solde fournisseurs")
screen("fournisseurs", "Répertoire des fournisseurs")
p("Le menu <b>Fournisseurs</b> gère le répertoire (nom, contact, adresse). "
  "Le menu <b>Solde Fournisseurs</b> gère l'argent que vous devez — ou que le fournisseur vous doit.")
screen("solde_fournisseurs", "Solde fournisseurs : dettes et avoirs")
h2("Dettes fournisseurs")
bullets([
    "Une dette est <b>créée automatiquement</b> à chaque validation d'approvisionnement.",
    "<b>Enregistrer un paiement</b> : partiel ou total (Espèces, Virement, Chèque).",
    "Les dettes de plus de 3 mois sont marquées <b>En retard</b>.",
    "<b>Abandon</b> : possibilité d'annuler une dette avec justification.",
])
h2("Avoirs fournisseurs (crédits)")
p("Un <b>avoir</b> représente une somme que le fournisseur vous doit, par exemple suite à une livraison "
  "incomplète ou des produits endommagés.")
steps([
    "Dans <b>Solde Fournisseurs</b>, cliquez sur <b>Créer un avoir</b>.",
    "Sélectionnez le fournisseur, le montant et le motif (produits manquants, endommagés…).",
    "L'avoir vient en <b>déduction du solde</b> dû à ce fournisseur.",
])

# ==================== 16. ORDONNANCES ====================
h1("16. Ordonnances")
steps([
    "Menu <b>Ordonnances</b> → <b>Nouvelle ordonnance</b>.",
    "Renseignez le patient, le médecin prescripteur et les médicaments prescrits.",
    "Lors de la délivrance des médicaments, mettez à jour le <b>statut</b> (en attente, partiellement délivrée, délivrée).",
])
p("L'historique complet des ordonnances est consultable et filtrable.")

# ==================== 17. RAPPORTS ====================
h1("17. Rapports et statistiques")
screen("rapports", "Page des rapports")
bullets([
    "<b>Ventes</b> : par période, par mode de paiement, avec détail des rabais accordés",
    "<b>Ventes partielles</b> et crédits en cours",
    "<b>Retours</b> : montants remboursés",
    "<b>Valorisation du stock</b> : valeur du stock au prix d'achat (FEFO)",
    "<b>Top produits</b> et évolution sur 7 jours",
])
tip("Les rapports sont réservés aux administrateurs et pharmaciens.")

# ==================== 18. UTILISATEURS ====================
h1("18. Utilisateurs (Admin)")
steps([
    "Menu <b>Utilisateurs</b> → <b>Nouvel utilisateur</b>.",
    "Renseignez le nom, l'e-mail, le mot de passe et le <b>rôle</b> (Admin, Pharmacien ou Caissier).",
    "Un <b>code employé</b> est attribué (ex. : ADM-001, CAI-002) — il apparaît dans les historiques.",
    "Enregistrez. L'utilisateur peut immédiatement se connecter.",
])
bullets([
    "Un utilisateur peut être <b>désactivé</b> sans être supprimé (il ne peut plus se connecter).",
    "Seul l'administrateur peut créer, modifier ou désactiver des comptes.",
])

# ==================== 19. PARAMETRES ====================
h1("19. Paramètres")
screen("parametres", "Page des paramètres")
table([
    [cell("<b>Paramètre</b>"), cell("<b>Rôle</b>")],
    [cell("Nom de la pharmacie"), cell("Affiché sur les reçus et documents.")],
    [cell("Devise"), cell("GNF par défaut.")],
    [cell("Seuil de stock bas"), cell("Déclenche les alertes de stock sur le tableau de bord.")],
    [cell("Délai de retour (jours)"), cell("Durée pendant laquelle un client peut retourner un produit (3 jours par défaut).")],
    [cell("Alerte péremption (jours)"), cell("Anticipation des alertes de péremption (30 jours par défaut).")],
    [cell("Dette en retard (jours)"), cell("Délai avant qu'une dette client soit marquée en retard (90 jours).")],
    [cell("Numéros Mobile Money"), cell("Numéros marchands Orange Money / MTN Money par défaut.")],
    [cell("Durée de shift par défaut"), cell("Durée maximale d'un shift (8 h par défaut).")],
    [cell("Fuseau horaire"), cell("Africa/Conakry par défaut.")],
    [cell("Méthode de valorisation"), cell("FEFO : premier périmé, premier sorti.")],
], col_widths=[6 * cm, 10.5 * cm])
p("La page Paramètres contient aussi la gestion du <b>mode hors-ligne</b> (voir chapitre suivant) et le bouton de "
  "téléchargement de ce <b>manuel d'utilisation</b>.")

# ==================== 20. OFFLINE ====================
h1("20. Mode hors-ligne (PWA)")
p("DynPharma continue de fonctionner en cas de coupure internet :")
bullets([
    "Les données essentielles (produits, clients, ventes récentes) sont <b>stockées localement</b> sur l'appareil.",
    "Un indicateur affiche l'état de la connexion et de la synchronisation.",
    "Les opérations effectuées hors-ligne sont mises en <b>file d'attente</b> puis synchronisées automatiquement dès le retour de la connexion.",
])
steps([
    "Dans <b>Paramètres</b>, utilisez <b>Précharger les données</b> pour garantir la disponibilité hors-ligne.",
    "En cas de doute, utilisez <b>Synchronisation complète</b> pour rafraîchir toutes les données locales.",
])
note("Pensez à précharger les données en début de journée si votre connexion est instable.")

# ==================== 21. FAQ ====================
h1("21. Questions fréquentes (FAQ)")
faq = [
    ("Je ne peux pas ouvrir mon shift, le bouton est grisé.",
     "Vous n'êtes pas planifié aujourd'hui, ou vous êtes en dehors de vos horaires. Contactez l'administrateur pour qu'il vous planifie dans le calendrier."),
    ("Le prix de vente d'un produit ne s'est pas mis à jour après une livraison.",
     "Vérifiez que l'approvisionnement a bien été <b>validé</b> (et pas seulement enregistré). C'est la validation qui met à jour le stock et les prix."),
    ("Une vente à crédit est refusée.",
     "Le client a probablement atteint son plafond de dette autorisé. Vérifiez sa fiche client ou encaissez d'abord un remboursement."),
    ("Le rabais s'applique-t-il automatiquement ?",
     "Oui : les règles automatiques (volume, fidélité, péremption) sont calculées en temps réel dans le panier. Une notification s'affiche quand un rabais est appliqué."),
    ("Comment corriger une erreur de vente ?",
     "Utilisez la fonction <b>Retour</b> depuis l'historique des ventes (dans le délai autorisé), puis refaites la vente correcte."),
    ("Que faire si l'application affiche « Hors ligne » ?",
     "Vous pouvez continuer à travailler. Les opérations seront synchronisées automatiquement au retour de la connexion. Ne fermez pas le navigateur avant la synchronisation."),
    ("Qui peut créer des comptes utilisateurs ?",
     "Uniquement l'administrateur, depuis le menu Utilisateurs."),
]
for q, a in faq:
    story.append(Paragraph(f"<b>❓ {q}</b>", st_h2))
    p(a)

# ==================== 22. GLOSSAIRE ====================
h1("22. Glossaire")
table([
    [cell("<b>Terme</b>"), cell("<b>Définition</b>")],
    [cell("Prix de cession (HT)"), cell("Prix d'achat du produit auprès du fournisseur, hors taxes. Base de calcul des approvisionnements.")],
    [cell("Prix public"), cell("Prix de vente au client = Prix de cession × Coefficient de marge.")],
    [cell("Coefficient de marge"), cell("Multiplicateur appliqué au prix de cession pour obtenir le prix public (1,4 par défaut).")],
    [cell("Shift"), cell("Session de caisse d'un employé, de l'ouverture à la fermeture avec comptage.")],
    [cell("Écart de caisse"), cell("Différence entre le montant théorique et le montant réellement compté à la fermeture.")],
    [cell("FEFO"), cell("First Expired, First Out : les lots qui périment en premier sont vendus en premier.")],
    [cell("Avoir fournisseur"), cell("Crédit dû par un fournisseur (livraison incomplète, produits endommagés).")],
    [cell("Dette client"), cell("Montant restant dû par un client suite à une vente à crédit ou partielle.")],
    [cell("Vente en attente"), cell("Vente mise en pause, reprise plus tard, sans impact sur le stock (expire après 24 h).")],
    [cell("TVA déductible"), cell("TVA payée sur les achats fournisseurs, récupérable fiscalement.")],
    [cell("PWA"), cell("Progressive Web App : application web installable qui fonctionne hors-ligne.")],
], col_widths=[4.5 * cm, 12 * cm])

story.append(Spacer(1, 20))
story.append(Paragraph("— Fin du manuel —", ParagraphStyle('end', parent=st_body, alignment=TA_CENTER)))


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(SLATE)
        canvas.drawString(2 * cm, 1.2 * cm, "DynPharma — Manuel d'utilisation")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=2 * cm, bottomMargin=2.2 * cm,
                        leftMargin=2 * cm, rightMargin=2 * cm,
                        title="Manuel d'utilisation DynPharma", author="DynPharma")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF généré: {OUT} ({os.path.getsize(OUT) / 1024:.0f} Ko)")
