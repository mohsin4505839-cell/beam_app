# cep_streamlit_expanded_fixed_long_v2.py
import streamlit as st
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
import pandas as pd
import io
from PIL import Image
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="CEP — Analysis & Design of Beam in Torsion", layout="wide")

# ---------------------------
# Visual / theme constants
# ---------------------------
BG_COLOR = "#2c2f33"
FG_COLOR = "#dcdcdc"
ACCENT_COLOR = "#4682b4"

# ---------------------------
# Bar diameter / area helpers (explicit copy)
# ---------------------------
BAR_DIAMETERS = {
    3: 0.375,
    4: 0.500,
    5: 0.625,
    6: 0.750,
    7: 0.875,
    8: 1.000,
    9: 1.128,
    10: 1.270,
    11: 1.410,
    14: 1.693,
    18: 2.257
}

def area_of_bar_explicit(bar_number):
    d = BAR_DIAMETERS.get(bar_number, 0)
    if d <= 0:
        return 0.0
    return round((math.pi / 4) * d ** 2, 6)

def area_of_bar(bar_number):
    d = BAR_DIAMETERS.get(bar_number, 0)
    return round((math.pi / 4) * d ** 2, 6) if d > 0 else 0.0

def _bar_diameter(bar_num):
    """Return dia in inches, fallback for unknown bar numbers."""
    try:
        return float(BAR_DIAMETERS.get(int(bar_num), 0.75))
    except Exception:
        return 0.75

# ---------------------------
# Safe parsing utilities (expanded)
# ---------------------------
def safe_float(value, name="value", default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception as e:
        raise ValueError(f"Invalid input for {name}: {e}")

def safe_int(value, name="value", default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception as e:
        raise ValueError(f"Invalid integer input for {name}: {e}")

# ---------------------------
# Section geometry helpers
# (explicit version + duplicate)
# ---------------------------
def compute_section_geometry(entries_b, entries_h, section_type, entries_tf=None):
    cover = 0.75
    b = float(entries_b)
    h = float(entries_h)
    if section_type == "T Section":
        tf = float(entries_tf)
        bf = b + 2 * min(4 * tf, h - tf)
        Acp = b * h + (bf - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (bf - b)
    elif section_type == "L Section":
        tf = float(entries_tf)
        bf = b + min(4 * tf, h - tf)
        Acp = b * h + (bf - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (bf - b)
    else:
        Acp = h * b
        Pcp = 2 * (h + b)

    Aoh = max((b - 2 * cover - 0.25), 0) * max((h - 2 * cover - 0.25), 0)
    Ph = 2 * max((b - 2 * cover - 0.25), 0) + 2 * max((h - 2 * cover - 0.25), 0)
    Ao = 0.85 * Aoh

    return {
        "Acp": Acp, "Pcp": Pcp, "Aoh": Aoh, "Ph": Ph, "Ao": Ao,
        "b": b, "h": h, "cover": cover, "bf": (bf if 'bf' in locals() else b), "tf": (entries_tf if entries_tf is not None else 0.0)
    }

def compute_section_geometry_dup(entries_b, entries_h, section_type, entries_tf=None):
    # duplicate of compute_section_geometry to mimic long Tk file structure
    cover = 0.75
    b = float(entries_b)
    h = float(entries_h)
    if section_type == "T Section":
        tf = float(entries_tf)
        bf = b + 2 * min(4 * tf, h - tf)
        Acp = b * h + (bf - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (bf - b)
    elif section_type == "L Section":
        tf = float(entries_tf)
        bf = b + min(4 * tf, h - tf)
        Acp = b * h + (bf - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (bf - b)
    else:
        Acp = h * b
        Pcp = 2 * (h + b)
    Aoh = max((b - 2 * cover - 0.25), 0) * max((h - 2 * cover - 0.25), 0)
    Ph = 2 * max((b - 2 * cover - 0.25), 0) + 2 * max((h - 2 * cover - 0.25), 0)
    Ao = 0.85 * Aoh
    return {"Acp": Acp, "Pcp": Pcp, "Aoh": Aoh, "Ph": Ph, "Ao": Ao, "b": b, "h": h, "cover": cover, "bf": (bf if 'bf' in locals() else b), "tf": (entries_tf if entries_tf is not None else 0.0)}

# ---------------------------
# Stirrup selection helper (duplicated)
# ---------------------------
def select_stirrup_and_spacing(Ph, Ats):
    bar_options = [3,4,5,6,7,8]
    selected_bar = None
    final_spacing = None
    if Ats <= 0 or Ph <= 0:
        return 3, max(4.0, min(12.0, Ph/8 if Ph>0 else 12.0))
    for bar in bar_options:
        Av = area_of_bar(bar)
        if Ats == 0:
            continue
        s = (2 * Av) / Ats
        if s <= min(Ph / 8, 12) and s >= 4:
            selected_bar = bar
            final_spacing = math.floor(s * 2) / 2
            break
    if selected_bar is None:
        selected_bar = 3
        s = min(Ph / 8, 12)
        final_spacing = math.floor(s * 2) / 2
    return selected_bar, final_spacing

def select_stirrup_and_spacing_dup(Ph, Ats):
    # duplicate variant to keep code verbose
    bar_options = [3, 4, 5, 6, 7, 8]
    if Ats <= 0:
        return 3, max(4.0, min(12.0, Ph/8 if Ph>0 else 12.0))
    for bar in bar_options:
        Av = area_of_bar_explicit(bar)
        if Ats == 0:
            continue
        s = (2 * Av) / Ats
        if 4 <= s <= min(Ph / 8 if Ph>0 else 12.0, 12.0):
            return bar, math.floor(s * 2) / 2
    return 3, math.floor(min(Ph / 8 if Ph>0 else 12.0, 12.0) * 2) / 2

# ---------------------------
# Core analysis functions (explicit for each section)
# ---------------------------
def analysis_rectangular(b, h, fc, tu_ft):
    try:
        cover = 0.75
        lamda = 1.0
        phi = 0.75
        Acp = b * h
        Pcp = 2 * (b + h)
        Aoh = max((b - 2 * cover), 0) * max((h - 2 * cover), 0)
        Ph = 2 * max((b - 2 * cover), 0) + 2 * max((h - 2 * cover), 0)
        Ao = 0.85 * Aoh
        sqrt_fc = math.sqrt(fc)
        Tcr = (4 * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
        Tth = Tcr / 4
        # message equivalent
        safe = tu_ft < Tth
        return {
            "Acp": Acp, "Pcp": Pcp, "Aoh": Aoh, "Ph": Ph, "Ao": Ao,
            "phiTcr": phi * Tcr, "Tth": Tth, "safe": safe
        }
    except Exception as e:
        raise

def analysis_T(b, h, tf, fc, tu_ft):
    try:
        cover = 0.75
        lamda = 1.0
        phi = 0.75
        x = min(h - tf, 4 * tf)
        b_total = b + 2 * x
        Acp = b * h + (b_total - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (b_total - b)
        Aoh = max((b - 2 * cover), 0) * max((h - 2 * cover), 0)
        Ph = 2 * max((b - 2 * cover), 0) + 2 * max((h - 2 * cover), 0)
        Ao = 0.85 * Aoh
        sqrt_fc = math.sqrt(fc)
        Tcr = (4 * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
        Tth = Tcr / 4
        safe = tu_ft < Tth
        return {"Acp": Acp, "Pcp": Pcp, "Aoh": Aoh, "Ph": Ph, "Ao": Ao, "phiTcr": phi * Tcr, "Tth": Tth, "safe": safe, "b_total": b_total, "x": x}
    except Exception as e:
        raise

def analysis_L(b, h, tf, fc, tu_ft):
    try:
        cover = 0.75
        lamda = 1.0
        phi = 0.75
        x = min(h - tf, 4 * tf)
        b_total = b + x
        Acp = b * h + (b_total - b) * tf
        Pcp = 2 * h + 2 * b + 2 * (b_total - b)
        Aoh = max((b - 2 * cover), 0) * max((h - 2 * cover), 0)
        Ph = 2 * max((b - 2 * cover), 0) + 2 * max((h - 2 * cover), 0)
        Ao = 0.85 * Aoh
        sqrt_fc = math.sqrt(fc)
        Tcr = (4 * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
        Tth = Tcr / 4
        safe = tu_ft < Tth
        return {"Acp": Acp, "Pcp": Pcp, "Aoh": Aoh, "Ph": Ph, "Ao": Ao, "phiTcr": phi * Tcr, "Tth": Tth, "safe": safe, "b_total": b_total, "x": x}
    except Exception as e:
        raise

# ---------------------------
# Design functions (Rectangular/T/L) - verbose
# ---------------------------
def design_rectangular(b, h, fc, fy, fyt, tu_ft, vu, bar_l, nl, As_flexure, nt, bar_top):
    vals = compute_section_geometry(b, h, "Rectangular", None)
    # replicate code from expanded clean version
    cover = 0.75
    lamda = 1.0
    phi = 0.75
    d = h - 2.5
    if d <= 0:
        raise ValueError("Effective depth d <= 0.")
    tu_in = tu_ft * 12
    sqrt_fc = math.sqrt(fc)
    Acp = vals["Acp"]; Pcp = vals["Pcp"]; Aoh = vals["Aoh"]; Ph = vals["Ph"]; Ao = vals["Ao"]
    phiTcr = (4 * phi * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
    Tth = phiTcr / 4
    if tu_ft < Tth:
        return {"safe": True, "phiTcr": phiTcr, "Tth": Tth}
    demand = math.sqrt(((vu * 1000) / (b * d)) ** 2 + (tu_in * 1000 * Ph / (1.7 * (Aoh ** 2))) ** 2)
    Vc = 2 * lamda * sqrt_fc * b * d
    phiVc = phi * Vc / 1000
    capacity = phi * ((Vc / (b * d)) + 8 * sqrt_fc)

    results = {}
    results["phiTcr"] = phiTcr
    results["Tth"] = Tth
    results["demand"] = demand
    results["Vc"] = Vc
    results["phiVc"] = phiVc
    results["capacity"] = capacity

    if demand <= capacity:
        Al = (tu_in * Ph) / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        At_s = tu_in / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        term1 = (5 * sqrt_fc * Acp / (1000 * fy)) - (At_s * Ph * fyt / fy)
        term2 = (5 * sqrt_fc * Acp / (1000 * fy)) - ((25 * b / fyt) * Ph * fyt / fy)
        Almin = max(term1, term2)
        if Al < Almin:
            Al = Almin
            results["Almin_governs"] = True
        results["Al"] = Al
        Vn = phiVc
        Vs = max(0.0, (vu - Vn) / phi)
        x = Vs / (fyt * d) if (fyt * d) != 0 else 0.0
        Ats = x + 2 * At_s
        Atsmin = max(0.75 * sqrt_fc * b / (1000 * fyt), 50 * b / (1000 * fyt))
        if Ats < Atsmin:
            Ats = Atsmin
        results["Vn"] = Vn
        results["Vs"] = Vs
        results["Ats"] = Ats
        results["Atsmin"] = Atsmin

        selected_bar, final_spacing = select_stirrup_and_spacing(Ph, Ats)
        results["stirrup_bar"] = selected_bar
        results["stirrup_spacing"] = final_spacing

        req_bottom = As_flexure + Al / 3.0
        req_mid = Al / 3.0
        top_bars_area = nt * area_of_bar(bar_top) if (nt > 0 and bar_top > 0) else 0.0
        req_top = top_bars_area + Al / 3.0

        area_bar_8 = area_of_bar(8)
        area_bar_6 = area_of_bar(6)

        num_bottom_bars_needed = math.ceil(req_bottom / area_bar_8) if area_bar_8>0 else 0
        num_top_bars_needed = math.ceil(req_top / area_bar_6) if area_bar_6>0 else 0

        required_per_bar = req_mid / 2 if req_mid>0 else 0.0
        mid_bar = next((bar for bar in range(3, 13) if area_of_bar(bar) >= required_per_bar), 3)
        area_mid = 2 * area_of_bar(mid_bar) if mid_bar else 0.0

        provided_bottom_by_user = nl * area_of_bar(bar_l)
        provided_top_by_user = nt * area_of_bar(bar_top) if (nt > 0 and bar_top > 0) else 0.0

        results.update({
            "req_bottom": req_bottom, "req_mid": req_mid, "req_top": req_top,
            "num_bottom_bars_needed": num_bottom_bars_needed, "num_top_bars_needed": num_top_bars_needed,"mid_bar": mid_bar,
            "area_mid": area_mid,
            "provided_bottom_by_user": provided_bottom_by_user, "provided_top_by_user": provided_top_by_user
        })
    else:
        results["demand_exceeds_capacity"] = True

    return results

def design_T(b, h, tf, fc, fy, fyt, tu_ft, vu, bar_l, nl, As_flexure, nt, bar_top):
    vals = compute_section_geometry_dup(b, h, "T Section", tf)
    cover = 0.75
    lamda = 1.0
    phi = 0.75
    d = h - 2.5
    if d <= 0:
        raise ValueError("Effective depth d <= 0.")
    tu_in = tu_ft * 12
    sqrt_fc = math.sqrt(fc)
    Acp = vals["Acp"]; Pcp = vals["Pcp"]; Aoh = vals["Aoh"]; Ph = vals["Ph"]; Ao = vals["Ao"]
    phiTcr = (4 * phi * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
    Tth = phiTcr / 4
    if tu_ft < Tth:
        return {"safe": True, "phiTcr": phiTcr, "Tth": Tth}
    demand = math.sqrt(((vu * 1000) / (b * d)) ** 2 + (tu_in * 1000 * Ph / (1.7 * (Aoh ** 2))) ** 2)
    Vc = 2 * lamda * sqrt_fc * b * d
    phiVc = phi * Vc / 1000
    capacity = phi * ((Vc / (b * d)) + 8 * sqrt_fc)

    results = {"phiTcr": phiTcr, "Tth": Tth, "demand": demand, "Vc": Vc, "phiVc": phiVc, "capacity": capacity}

    if demand <= capacity:
        Al = (tu_in * Ph) / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        At_s = tu_in / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        term1 = (5 * sqrt_fc * Acp / (1000 * fy)) - (At_s * Ph * fyt / fy)
        term2 = (5 * sqrt_fc * Acp / (1000 * fy)) - ((25 * b / fyt) * Ph * fyt / fy)
        Almin = max(term1, term2)
        if Al < Almin:
            Al = Almin
            results["Almin_governs"] = True
        results["Al"] = Al
        Vn = phiVc
        Vs = max(0.0, (vu - Vn) / phi)
        x = Vs / (fyt * d) if (fyt * d) != 0 else 0.0
        Ats = x + 2 * At_s
        Atsmin = max(0.75 * sqrt_fc * b / (1000 * fyt), 50 * b / (1000 * fyt))
        if Ats < Atsmin:
            Ats = Atsmin
        results.update({"Vn": Vn, "Vs": Vs, "Ats": Ats, "Atsmin": Atsmin})

        selected_bar, final_spacing = select_stirrup_and_spacing_dup(Ph, Ats)
        results["stirrup_bar"] = selected_bar
        results["stirrup_spacing"] = final_spacing

        req_bottom = As_flexure + Al / 3.0
        req_mid = Al / 3.0
        top_bars_area = nt * area_of_bar_explicit(bar_top) if (nt > 0 and bar_top > 0) else 0.0
        req_top = top_bars_area + Al / 3.0

        area_bar_8 = area_of_bar_explicit(8)
        area_bar_6 = area_of_bar_explicit(6)

        num_bottom_bars_needed = math.ceil(req_bottom / area_bar_8) if area_bar_8>0 else 0
        num_top_bars_needed = math.ceil(req_top / area_bar_6) if area_bar_6>0 else 0

        required_per_bar = req_mid / 2 if req_mid>0 else 0.0
        mid_bar = next((bar for bar in range(3, 13) if area_of_bar_explicit(bar) >= required_per_bar), 3)
        area_mid = 2 * area_of_bar_explicit(mid_bar) if mid_bar else 0.0

        provided_bottom_by_user = nl * area_of_bar(bar_l)
        provided_top_by_user = nt * area_of_bar(bar_top) if (nt > 0 and bar_top > 0) else 0.0

        results.update({
            "req_bottom": req_bottom, "req_mid": req_mid, "req_top": req_top,
            "num_bottom_bars_needed": num_bottom_bars_needed, "num_top_bars_needed": num_top_bars_needed,
            "mid_bar": mid_bar, "area_mid": area_mid, "provided_bottom_by_user": provided_bottom_by_user,
            "provided_top_by_user": provided_top_by_user
        })
    else:
        results["demand_exceeds_capacity"] = True

    return results

def design_L(b, h, tf, fc, fy, fyt, tu_ft, vu, bar_l, nl, As_flexure, nt, bar_top):
    vals = compute_section_geometry(b, h, "L Section", tf)
    cover = 0.75
    lamda = 1.0
    phi = 0.75
    d = h - 2.5
    if d <= 0:
        raise ValueError("Effective depth d <= 0.")
    tu_in = tu_ft * 12
    sqrt_fc = math.sqrt(fc)
    Acp = vals["Acp"]; Pcp = vals["Pcp"]; Aoh = vals["Aoh"]; Ph = vals["Ph"]; Ao = vals["Ao"]
    phiTcr = (4 * phi * lamda * sqrt_fc * (Acp ** 2) / Pcp) / (1000 * 12)
    Tth = phiTcr / 4
    if tu_ft < Tth:
        return {"safe": True, "phiTcr": phiTcr, "Tth": Tth}
    demand = math.sqrt(((vu * 1000) / (b * d)) ** 2 + (tu_in * 1000 * Ph / (1.7 * (Aoh ** 2))) ** 2)
    Vc = 2 * lamda * sqrt_fc * b * d
    phiVc = phi * Vc / 1000
    capacity = phi * ((Vc / (b * d)) + 8 * sqrt_fc)

    results = {"phiTcr": phiTcr, "Tth": Tth, "demand": demand, "Vc": Vc, "phiVc": phiVc, "capacity": capacity}

    if demand <= capacity:
        Al = (tu_in * Ph) / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        At_s = tu_in / (phi * 2 * Ao * fy) if Ao > 0 else float('inf')
        term1 = (5 * sqrt_fc * Acp / (1000 * fy)) - (At_s * Ph * fyt / fy)
        term2 = (5 * sqrt_fc * Acp / (1000 * fy)) - ((25 * b / fyt) * Ph * fyt / fy)
        Almin = max(term1, term2)
        if Al < Almin:
            Al = Almin
            results["Almin_governs"] = True
        results["Al"] = Al
        Vn = phiVc
        Vs = max(0.0, (vu - Vn) / phi)
        x = Vs / (fyt * d) if (fyt * d) != 0 else 0.0
        Ats = x + 2 * At_s
        Atsmin = max(0.75 * sqrt_fc * b / (1000 * fyt), 50 * b / (1000 * fyt))
        if Ats < Atsmin:
            Ats = Atsmin
        results.update({"Vn": Vn, "Vs": Vs, "Ats": Ats, "Atsmin": Atsmin})

        selected_bar, final_spacing = select_stirrup_and_spacing(Ph, Ats)
        results["stirrup_bar"] = selected_bar
        results["stirrup_spacing"] = final_spacing

        req_bottom = As_flexure + Al / 3.0
        req_mid = Al / 3.0
        top_bars_area = nt * area_of_bar(bar_top) if (nt > 0 and bar_top > 0) else 0.0
        req_top = top_bars_area + Al / 3.0

        area_bar_8 = area_of_bar(8)
        area_bar_6 = area_of_bar(6)

        num_bottom_bars_needed = math.ceil(req_bottom / area_bar_8) if area_bar_8>0 else 0
        num_top_bars_needed = math.ceil(req_top / area_bar_6) if area_bar_6>0 else 0

        required_per_bar = req_mid / 2 if req_mid>0 else 0.0
        mid_bar = next((bar for bar in range(3, 13) if area_of_bar(bar) >= required_per_bar), 3)
        area_mid = 2 * area_of_bar(mid_bar) if mid_bar else 0.0

        provided_bottom_by_user = nl * area_of_bar(bar_l)
        provided_top_by_user = nt * area_of_bar(bar_top) if (nt > 0 and bar_top > 0) else 0.0

        results.update({
            "req_bottom": req_bottom, "req_mid": req_mid, "req_top": req_top,
            "num_bottom_bars_needed": num_bottom_bars_needed, "num_top_bars_needed": num_top_bars_needed,
            "mid_bar": mid_bar, "area_mid": area_mid, "provided_bottom_by_user": provided_bottom_by_user,
            "provided_top_by_user": provided_top_by_user
        })
    else:
        results["demand_exceeds_capacity"] = True

    return results

# ---------------------------
# Drawing helpers (improved & consolidated)
# ---------------------------

def _draw_circle(ax, cx, cy, r, edge='black', face='#2B7ABF', zorder=5):
    c = Circle((cx, cy), r, edgecolor=edge, facecolor=face, linewidth=1.2, zorder=zorder)
    ax.add_patch(c)

def _draw_double_arrow(ax, x1, y1, x2, y2, text, rot=0, txt_offset=(0,0)):
    ax.annotate('', xy=(x1, y1), xytext=(x2, y2),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.1))
    tx = (x1 + x2) / 2 + txt_offset[0]
    ty = (y1 + y2) / 2 + txt_offset[1]
    ax.text(tx, ty, text, ha='center', va='center', rotation=rot, fontsize=9, bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"))

def _draw_callout_arrow(ax, tail_x, tail_y, head_x, head_y, label, tail_offset=(6,-6)):
    ax.annotate('', xy=(head_x, head_y), xytext=(tail_x, tail_y),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.6))
    ax.text(tail_x + tail_offset[0], tail_y + tail_offset[1], label, fontsize=10, color='black')

def draw_rectangular_layout(b, h, num_top, num_bottom, mid_bar, stirrup_bar, stirrup_spacing, show_bar_spacing=False):
    # scale so drawing is large and similar to sample
    fig, ax = plt.subplots(figsize=(10,6))
    scale = 12.0  # pixels per inch
    width = b * scale
    height = h * scale

    # Outer thick border
    outer_thickness = 6
    outer = FancyBboxPatch((0,0), width, height,
                           boxstyle="round,pad=0.02", linewidth=outer_thickness,
                           edgecolor='black', facecolor='#e6e6e6')
    ax.add_patch(outer)

    # Inner hollow/web rectangle (representing hole / clear area)
    cover = 0.75  # in
    cover_px = cover * scale
    inner_left = cover_px + 10
    inner_right = width - cover_px - 10
    inner_bottom = cover_px + 10
    inner_top = height - cover_px - 10
    inner_width = inner_right - inner_left
    inner_height = inner_top - inner_bottom

    inner = Rectangle((inner_left, inner_bottom), inner_width, inner_height,
                      linewidth=4, edgecolor='#333333', facecolor='#ffffff')
    ax.add_patch(inner)

    # Draw cover arrow and label
    cover_arrow_x1 = 2
    ax.annotate('', xy=(cover_arrow_x1, inner_top - inner_height/2), xytext=(inner_left, inner_top - inner_height/2),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
    ax.text((cover_arrow_x1 + inner_left)/2, inner_top - inner_height/2 + 8, f"cover = {cover:.2f} in", fontsize=9, ha='center')

    # Place bars: we will place num_top along top row inside inner rect,
    # 2 mid bars at mid depth (left and right), and num_bottom along bottom.
    r_px = 10  # radius in px for drawn reinforcement circles

    # Top bars
    top_coords = []
    if num_top > 0:
        if num_top > 1:
            spacing_top = (inner_width - 2*r_px - 4) / (num_top - 1)
        else:
            spacing_top = 0
        y_top = inner_top - r_px - 6
        for i in range(num_top):
            cx = inner_left + r_px + 2 + i * spacing_top
            _draw_circle(ax, cx, y_top, r_px)
            top_coords.append((cx, y_top))
    else:
        top_coords = []

    # Mid bars: typically 2 bars left/right
    y_mid = inner_bottom + inner_height / 2
    mid_left = (inner_left + r_px + 8, y_mid)
    mid_right = (inner_right - r_px - 8, y_mid)
    _draw_circle(ax, *mid_left, r_px)
    _draw_circle(ax, *mid_right, r_px)
    mid_coords = [mid_left, mid_right]

    # Bottom bars
    bottom_coords = []
    if num_bottom > 0:
        if num_bottom > 1:
            spacing_bottom = (inner_width - 2*r_px - 4) / (num_bottom - 1)
        else:
            spacing_bottom = 0
        y_bottom = inner_bottom + r_px + 6
        for i in range(num_bottom):
            cx = inner_left + r_px + 2 + i * spacing_bottom
            _draw_circle(ax, cx, y_bottom, r_px)
            bottom_coords.append((cx, y_bottom))

    # Add dimension arrows: b and h
    # b along top (outside)
    _draw_double_arrow(ax, 0, height + 18, width, height + 18, f"b = {b:.2f} in")
    # h along left
    _draw_double_arrow(ax, -48, 0, -48, height, f"h = {h:.2f} in", rot=90)

    # Add labels with red arrows (right side)
    labels_x = width + 80
    # top label
    if top_coords:
        tx, ty = top_coords[0]
        _draw_callout_arrow(ax, labels_x, ty + 4, tx + r_px + 5, ty, f"{num_top} × #{6} (top)")
    # mid label
    _draw_callout_arrow(ax, labels_x, y_mid + 2, mid_right[0] + r_px + 5, y_mid, f"2 × #{mid_bar} (mid)")
    # stirrups label
    _draw_callout_arrow(ax, labels_x, y_mid - 30, inner_right + 5, y_mid - inner_height/6,
                     f"#{stirrup_bar} stirrups @ {stirrup_spacing:.2f} in c/c")
    # bottom label
    if bottom_coords:
        bx, by = bottom_coords[0]
        _draw_callout_arrow(ax, labels_x, by - 30, bx + r_px + 5, by, f"{num_bottom} × #{8} (bottom)")

    # optionally show spacing between bottom bars as a dimension on bottom row
    if show_bar_spacing and len(bottom_coords) > 1:
        x_first = bottom_coords[0][0]
        x_last = bottom_coords[-1][0]
        spacing_in = (x_last - x_first) / (len(bottom_coords)-1) / scale if len(bottom_coords) > 1 else 0
        _draw_double_arrow(ax, x_first, y_bottom - 25, x_last, y_bottom - 25, f"{spacing_in:.2f} in spacing")

    ax.set_xlim(-160, width + 260)
    ax.set_ylim(-80, height + 120)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

def draw_T_layout(b, h, tf, num_top, num_bottom, mid_bar, stirrup_bar, stirrup_spacing, show_bar_spacing=False):
    fig, ax = plt.subplots(figsize=(11,7))
    scale = 12.0
    bf = (b + 2 * min(4 * tf, h - tf))
    Bf_px = bf * scale
    Tf_px = tf * scale
    Bw_px = b * scale
    D_px = h * scale

    base_x = 40
    base_y = 40

    flange_left = base_x
    flange_right = base_x + Bf_px
    flange_top = base_y + D_px - Tf_px
    flange_bottom = base_y + D_px

    # Draw outer flange rectangle (top)
    ax.add_patch(Rectangle((flange_left, flange_top), Bf_px, Tf_px, edgecolor='black', facecolor='#e6e6e6', linewidth=4))
    # Draw web rectangle (below flange)
    web_left = base_x + (Bf_px - Bw_px)/2
    web_bottom = base_y
    web_height = D_px - Tf_px
    ax.add_patch(Rectangle((web_left, web_bottom), Bw_px, web_height, edgecolor='black', facecolor='#ffffff', linewidth=4))

    # hollow inner area inside web (representing clear area)
    cover = 0.75
    cover_px = cover * scale
    hollow_left = web_left + cover_px + 6
    hollow_right = web_left + Bw_px - cover_px - 6
    hollow_top = flange_top - 6
    hollow_bottom = web_bottom + cover_px + 6
    hollow_w = hollow_right - hollow_left
    hollow_h = hollow_top - hollow_bottom
    ax.add_patch(Rectangle((hollow_left, hollow_bottom), hollow_w, hollow_h, edgecolor='#333333', facecolor='#ffffff', linewidth=3))

    # dimension labels bf and h
    ax.text((flange_left + flange_right)/2, flange_bottom + 16, f"bf = {bf:.2f} in   tf = {tf:.2f} in", ha='center', fontsize=9)
    _draw_double_arrow(ax, -60, web_bottom, -60, flange_bottom, f"h = {h:.2f} in", rot=90)

    r_px = 10
    # top bars inside flange (if any) - place in hollow top region
    top_coords = []
    if num_top > 0:
        if num_top > 1:
            spacing_top = (hollow_w - 2*r_px - 4) / (num_top - 1)
        else:
            spacing_top = 0
        y_top = hollow_top - r_px - 6
        for i in range(num_top):
            cx = hollow_left + r_px + 2 + i * spacing_top
            _draw_circle(ax, cx, y_top, r_px)
            top_coords.append((cx, y_top))

    # mid bars: put two in web left/right interior
    y_mid = hollow_bottom + hollow_h / 2
    mid_left = (hollow_left + r_px + 6, y_mid)
    mid_right = (hollow_right - r_px - 6, y_mid)
    _draw_circle(ax, *mid_left, r_px)
    _draw_circle(ax, *mid_right, r_px)

    # bottom bars inside hollow bottom
    bottom_coords = []
    if num_bottom > 0:
        if num_bottom > 1:
            spacing_bottom = (hollow_w - 2*r_px - 4) / (num_bottom - 1)
        else:
            spacing_bottom = 0
        y_bottom = hollow_bottom + r_px + 6
        for i in range(num_bottom):
            cx = hollow_left + r_px + 2 + i * spacing_bottom
            _draw_circle(ax, cx, y_bottom, r_px)
            bottom_coords.append((cx, y_bottom))

    # labels with arrows to right
    label_x = flange_right + 80
    if top_coords:
        tx, ty = top_coords[0]
        _draw_callout_arrow(ax, label_x, ty + 6, tx + r_px + 3, ty, f"{num_top} × #{6} (top)")
    _draw_callout_arrow(ax, label_x, y_mid, mid_right[0] + r_px + 3, y_mid, f"2 × #{mid_bar} (mid)")
    if bottom_coords:
        bx, by = bottom_coords[0]
        _draw_callout_arrow(ax, label_x, by - 18, bx + r_px + 3, by, f"{num_bottom} × #{8} (bottom)")
    _draw_callout_arrow(ax, label_x, y_mid - 36, hollow_right + 6, y_mid - hollow_h/4, f"#{stirrup_bar} stirrups @ {stirrup_spacing:.2f} in c/c")

    # optionally show bottom spacing dimension
    if show_bar_spacing and len(bottom_coords) > 1:
        x_first = bottom_coords[0][0]
        x_last = bottom_coords[-1][0]
        spacing_in = (x_last - x_first) / (len(bottom_coords)-1) / scale if len(bottom_coords) > 1 else 0
        _draw_double_arrow(ax, x_first, hollow_bottom - 28, x_last, hollow_bottom - 28, f"{spacing_in:.2f} in spacing")

    ax.set_xlim(-160, flange_right + 260)
    ax.set_ylim(-100, flange_bottom + 120)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

def draw_L_layout(b, h, tf, num_top, num_bottom, mid_bar, stirrup_bar, stirrup_spacing, show_bar_spacing=False):
    fig, ax = plt.subplots(figsize=(11,7))
    scale = 12.0
    bf = (b + min(4 * tf, h - tf))
    bf_px = bf * scale
    Tf_px = tf * scale
    Bw_px = b * scale
    D_px = h * scale

    base_x = 40
    base_y = 40

    flange_left = base_x
    flange_right = base_x + bf_px
    flange_top = base_y + D_px - Tf_px
    flange_bottom = base_y + D_px

    # Draw flange (horizontal) and web (vertical)
    ax.add_patch(Rectangle((flange_left, flange_top), bf_px, Tf_px, edgecolor='black', facecolor='#e6e6e6', linewidth=4))
    web_left = base_x + (bf_px - Bw_px) / 2
    web_bottom = base_y
    web_height = D_px - Tf_px
    ax.add_patch(Rectangle((web_left, web_bottom), Bw_px, web_height, edgecolor='black', facecolor='#ffffff', linewidth=4))

    # hollow inner area
    cover = 0.75
    cover_px = cover * scale
    hollow_left = web_left + cover_px + 6
    hollow_right = web_left + Bw_px - cover_px - 6
    hollow_top = flange_top - 6
    hollow_bottom = web_bottom + cover_px + 6
    hollow_w = hollow_right - hollow_left
    hollow_h = hollow_top - hollow_bottom
    ax.add_patch(Rectangle((hollow_left, hollow_bottom), hollow_w, hollow_h, edgecolor='#333333', facecolor='#ffffff', linewidth=3))

    # dims
    ax.text((flange_left + flange_right)/2, flange_bottom + 16, f"bf = {bf:.2f} in   tf = {tf:.2f} in", ha='center', fontsize=9)
    _draw_double_arrow(ax, -60, web_bottom, -60, flange_bottom, f"h = {h:.2f} in", rot=90)

    r_px = 10
    top_coords = []
    if num_top > 0:
        if num_top > 1:
            spacing_top = (hollow_w - 2*r_px - 4) / (num_top - 1)
        else:
            spacing_top = 0
        y_top = hollow_top - r_px - 6
        for i in range(num_top):
            cx = hollow_left + r_px + 2 + i * spacing_top
            _draw_circle(ax, cx, y_top, r_px)
            top_coords.append((cx, y_top))

    # mid bars
    y_mid = hollow_bottom + hollow_h / 2
    mid_left = (hollow_left + r_px + 6, y_mid)
    mid_right = (hollow_right - r_px - 6, y_mid)
    _draw_circle(ax, *mid_left, r_px)
    _draw_circle(ax, *mid_right, r_px)

    # bottom bars
    bottom_coords = []
    if num_bottom > 0:
        if num_bottom > 1:
            spacing_bottom = (hollow_w - 2*r_px - 4) / (num_bottom - 1)
        else:
            spacing_bottom = 0
        y_bottom = hollow_bottom + r_px + 6
        for i in range(num_bottom):
            cx = hollow_left + r_px + 2 + i * spacing_bottom
            _draw_circle(ax, cx, y_bottom, r_px)
            bottom_coords.append((cx, y_bottom))

    label_x = flange_right + 80
    if top_coords:
        tx, ty = top_coords[0]
        _draw_callout_arrow(ax, label_x, ty + 6, tx + r_px + 3, ty, f"{num_top} × #{6} (top)")
    _draw_callout_arrow(ax, label_x, y_mid, mid_right[0] + r_px + 3, y_mid, f"2 × #{mid_bar} (mid)")
    if bottom_coords:
        bx, by = bottom_coords[0]
        _draw_callout_arrow(ax, label_x, by - 18, bx + r_px + 3, by, f"{num_bottom} × #{8} (bottom)")
    _draw_callout_arrow(ax, label_x, y_mid - 36, hollow_right + 6, y_mid - hollow_h/4, f"#{stirrup_bar} stirrups @ {stirrup_spacing:.2f} in c/c")

    if show_bar_spacing and len(bottom_coords) > 1:
        x_first = bottom_coords[0][0]
        x_last = bottom_coords[-1][0]
        spacing_in = (x_last - x_first) / (len(bottom_coords)-1) / scale if len(bottom_coords) > 1 else 0
        _draw_double_arrow(ax, x_first, hollow_bottom - 28, x_last, hollow_bottom - 28, f"{spacing_in:.2f} in spacing")

    ax.set_xlim(-160, flange_right + 260)
    ax.set_ylim(-100, flange_bottom + 120)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

# ---------------------------
# Streamlit UI — Professional polished layout (sidebar mode, theme toggle, results table)
# This block replaces the previous Streamlit UI block.
# ---------------------------

# Theme control state
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"  # default

def set_theme(theme):
    st.session_state["theme"] = theme

# Sidebar controls
with st.sidebar:
    st.markdown("## CEP — Controls", unsafe_allow_html=True)
    mode = st.radio("Mode", ["Analysis", "Design"], index=0)
    st.markdown("---")
    theme_choice = st.selectbox("Theme", ["Dark", "Light"], index=0 if st.session_state["theme"]=="dark" else 1)
    if theme_choice == "Dark":
        set_theme("dark")
    else:
        set_theme("light")

    st.markdown("---")
    st.caption("Use 'Run Calculation' then tick the Draw checkbox to display cross-section layout.")

    # MOVED: Section type to sidebar as requested
    st.markdown('<div class="section-header">Section Type</div>', unsafe_allow_html=True)
    want_section = st.selectbox("Section Type", ["Rectangular Section", "T Section", "L Section"], index=0)
    if want_section in ("T Section", "L Section"):
        tf_sidebar = st.number_input("Flange thickness tf (in)", value=1.0, step=0.25, format="%.3f", key="tf_sidebar")
    else:
        tf_sidebar = None

# CSS for professional typography and theme colors (applies to page)
if st.session_state["theme"] == "dark":
    primary_bg = "#0f1720"
    secondary_bg = "#111827"
    text_color = "#E6EEF3"
    muted = "#9AA6B2"
    card_bg = "#0b1220"
else:
    primary_bg = "#FFFFFF"
    secondary_bg = "#F3F6F9"
    text_color = "#0f1720"
    muted = "#44505A"
    card_bg = "#FFFFFF"

st.markdown(f"""
    <style>
        /* overall page */
        .reportview-container, .main {{
            background: linear-gradient(0deg, {secondary_bg}, {primary_bg});
        }}
        /* title */
        .big-title {{
            font-family: "Helvetica Neue", Arial, sans-serif;
            font-size: 26px;
            font-weight: 700;
            color: {text_color};
            margin-bottom: 6px;
        }}
        /* section headers */
        .section-header {{
            font-family: "Inter", Arial, sans-serif;
            font-size: 14px;
            color: {text_color};
            margin-top: 8px;
            margin-bottom: 6px;
            font-weight:600;
        }}
        /* caption / muted */
        .muted {{
            color: {muted};
            font-size:12px;
        }}
        /* cards */
        .stCard {{
            background: {card_bg} !important;
            padding: 12px;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        }}
        /* small inputs spacing */
        .stNumberInput, .stSelectbox {{
            margin-bottom: 6px;
        }}
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown(f'<div class="big-title">CEP — Analysis & Design of Beam in Torsion</div>', unsafe_allow_html=True)

# Two-column main layout: left = inputs, right = results + drawings
left_col, right_col = st.columns([1, 1.25], gap="large")

with left_col:
    st.markdown('<div class="section-header">Inputs — Loads & Material</div>', unsafe_allow_html=True)
    # useful sensible defaults, compact layout
    vu = st.number_input("Vu (kips)", value=10.0, step=1.0, format="%.3f", key="vu")
    tu = st.number_input("Tu (kips-ft)", value=0.0, step=0.5, format="%.3f", key="tu")
    fc = st.number_input("f'c (psi)", value=4000.0, step=100.0, format="%.1f", key="fc")

    # Show design-only material inputs only when Design mode is selected
    if mode == "Design":
        fy = st.number_input("fy (ksi)", value=60.0, step=1.0, format="%.3f", key="fy")
        fyt = st.number_input("fyt (ksi)", value=60.0, step=1.0, format="%.3f", key="fyt")
    else:
        # set defaults so downstream functions won't break
        fy = 60.0
        fyt = 60.0

    st.markdown('<div class="section-header">Geometry (inches)</div>', unsafe_allow_html=True)
    h = st.number_input("Beam height h (in)", value=12.0, step=0.5, format="%.3f", key="h")
    b = st.number_input("Beam or web width b (in)", value=8.0, step=0.5, format="%.3f", key="b")

    # use tf from sidebar if section type needs it
    tf = tf_sidebar

    # Longitudinal reinforcement / user-provided: show only in Design mode
    st.markdown('<div class="section-header">Longitudinal reinforcement / user-provided</div>', unsafe_allow_html=True)
    if mode == "Design":
        nl = st.number_input("No. of bottom longitudinal bars (Nl)", min_value=0, value=2, step=1, key="nl")
        bar_l = st.selectbox("Longitudinal bar # (bottom)", [3,4,5,6,7,8,9,10], index=3, key="bar_l")
        nt = st.number_input("No. of top longitudinal bars (Nt)", min_value=0, value=0, step=1, key="nt")
        bar_top = st.selectbox("Top longitudinal bar #", [3,4,5,6,7,8,9,10], index=3, key="bar_top")
        As_flexure = st.number_input("Area of steel required for flexure As_flexure (in²)", value=0.5, step=0.01, format="%.4f", key="As_flexure")
    else:
        # dummy defaults for analysis mode
        nl = 0
        bar_l = 3
        nt = 0
        bar_top = 3
        As_flexure = 0.0

    st.markdown("---")
    # Buttons arranged horizontally
    run_col1, run_col2 = st.columns([1,1])
    with run_col1:
        run_calc = st.button("Run Calculation", key="run_calc")
    with run_col2:
        draw_checkbox = st.checkbox("Draw Cross-Section after calculation", value=False, key="draw_checkbox")

    st.markdown('<div class="muted">Tip: Run calculation first. Results will appear on the right in a table. Then enable Draw to show the cross-section plot.</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-header">Results</div>', unsafe_allow_html=True)

    # placeholder for result table and messages
    result_placeholder = st.empty()
    draw_placeholder = st.empty()

# --- Run calculations (using your existing compute/design functions) ---
calculated = None
if run_calc:
    try:
        vals = compute_section_geometry(b, h, want_section, tf)
        st.session_state["last_inputs"] = {"b": b, "h": h, "tf": tf, "section": want_section,
                                           "nl": nl, "bar_l": bar_l, "nt": nt, "bar_top": bar_top,
                                           "As_flexure": As_flexure, "vu": vu, "tu": tu, "fc": fc, "fy": fy, "fyt": fyt, "mode": mode}
        if mode == "Analysis":
            if want_section == "Rectangular Section":
                out = analysis_rectangular(b, h, fc, tu)
            elif want_section == "T Section":
                out = analysis_T(b, h, tf, fc, tu)
            else:
                out = analysis_L(b, h, tf, fc, tu)
        else:  # Design
            if want_section == "Rectangular Section":
                out = design_rectangular(b, h, fc, fy, fyt, tu, vu, bar_l, nl, As_flexure, nt, bar_top)
            elif want_section == "T Section":
                out = design_T(b, h, tf, fc, fy, fyt, tu, vu, bar_l, nl, As_flexure, nt, bar_top)
            else:
                out = design_L(b, h, tf, fc, fy, fyt, tu, vu, bar_l, nl, As_flexure, nt, bar_top)

        # Merge geometry & outputs for table
        merged = {**vals, **out}
        # Flatten and filter numeric/key results to present professionally
        keys_order = ["b","h","tf","Acp","Pcp","Aoh","Ph","Ao","phiTcr","Tth","Vc","phiVc","capacity","Al","Ats","Atsmin",
                      "stirrup_bar","stirrup_spacing","req_bottom","req_mid","req_top","num_bottom_bars_needed","num_top_bars_needed","mid_bar"]
        rows = []
        for k in keys_order:
            if k in merged:
                rows.append((k, merged[k]))

        # Create DataFrame for display
        df = pd.DataFrame(rows, columns=["Parameter","Value"])
        # pretty formatting for numeric
        def fmt(v):
            try:
                if isinstance(v, float):
                    return f"{v:.4f}"
                else:
                    return str(v)
            except:
                return str(v)

        df["Value"] = df["Value"].apply(fmt)
        # Save to session for drawing use
        st.session_state["last_calc"] = merged
        calculated = merged

        # show table in the right column
        with result_placeholder.container():
            st.markdown("**Calculated results (table)**")
            st.dataframe(df, width='stretch')

            # friendly messages
            if merged.get("safe", False):
                st.success("Tu < Tth → Section is safe in torsion. No torsional reinforcement required.")
            elif merged.get("demand_exceeds_capacity", False):
                st.error("Demand exceeds capacity — torsion/shear capacity insufficient.")
            else:
                st.info("Design/analysis completed — see details above.")

    except Exception as e:
        result_placeholder.error(f"Calculation error: {e}")
        calculated = None

# Drawing logic (draw only if user asked)
last_figure_bytes = None
if draw_checkbox:
    # prefer using last saved calc if available
    out = st.session_state.get("last_calc") or calculated
    if out is None:
        draw_placeholder.error("No calculation found. Run 'Run Calculation' first.")
    else:
        # choose layout function based on section
        st.markdown('<div class="section-header">Cross-section Layout</div>', unsafe_allow_html=True)
        fig = None
        show_bar_spacing = st.checkbox("Annotate spacing between longitudinal bars", value=False, key="draw_spacing")
        if want_section == "Rectangular Section":
            num_top = out.get("num_top_bars_needed") if out.get("num_top_bars_needed") else st.session_state["last_inputs"].get("nt",0)
            num_bottom = out.get("num_bottom_bars_needed") if out.get("num_bottom_bars_needed") else st.session_state["last_inputs"].get("nl",0)
            fig = draw_rectangular_layout(out["b"], out["h"], num_top, num_bottom, out.get("mid_bar",6), out.get("stirrup_bar",3), out.get("stirrup_spacing",6.0), show_bar_spacing)
        elif want_section == "T Section":
            num_top = out.get("num_top_bars_needed") if out.get("num_top_bars_needed") else st.session_state["last_inputs"].get("nt",0)
            num_bottom = out.get("num_bottom_bars_needed") if out.get("num_bottom_bars_needed") else st.session_state["last_inputs"].get("nl",0)
            tf_draw = out.get("tf") if out.get("tf") else (tf if tf else 1.0)
            fig = draw_T_layout(out["b"], out["h"], tf_draw, num_top, num_bottom, out.get("mid_bar",6), out.get("stirrup_bar",3), out.get("stirrup_spacing",6.0), show_bar_spacing)
        else:  # L
            num_top = out.get("num_top_bars_needed") if out.get("num_top_bars_needed") else st.session_state["last_inputs"].get("nt",0)
            num_bottom = out.get("num_bottom_bars_needed") if out.get("num_bottom_bars_needed") else st.session_state["last_inputs"].get("nl",0)
            tf_draw = out.get("tf") if out.get("tf") else (tf if tf else 1.0)
            fig = draw_L_layout(out["b"], out["h"], tf_draw, num_top, num_bottom, out.get("mid_bar",6), out.get("stirrup_bar",3), out.get("stirrup_spacing",6.0), show_bar_spacing)

        if fig is not None:
            draw_placeholder.pyplot(fig)
            # save figure to bytes so it can be embedded in PDF
            buf = io.BytesIO()
            fig.tight_layout()
            fig.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            last_figure_bytes = buf.read()

# --- PDF Report Generation ---
# Button / option to generate a professional PDF report containing all inputs, step-by-step calculations and drawings
if st.button("Generate professional PDF report (Download)"):
    report_buf = io.BytesIO()
    # create pdf
    c = pdf_canvas.Canvas(report_buf, pagesize=A4)
    width, height = A4
    margin = 40

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - margin, "CEP — Professional Calculation Report")
    c.setFont("Helvetica", 10)
    c.drawString(margin, height - margin - 18, f"Mode: {mode}    Section: {want_section}")

    # Inputs block
    y = height - margin - 48
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "1) Inputs & Material")
    y -= 16
    c.setFont("Helvetica", 10)
    inputs_text = [
        f"Vu (kips): {vu}", f"Tu (kips-ft): {tu}", f"f'c (psi): {fc}", f"fy (ksi): {fy}", f"fyt (ksi): {fyt}",
        f"Beam h (in): {h}", f"Beam b (in): {b}", f"tf (in): {tf}",
        f"Bottom bars Nl: {nl} (#{bar_l})", f"Top bars Nt: {nt} (#{bar_top})", f"As_flexure (in2): {As_flexure}"
    ]
    for line in inputs_text:
        c.drawString(margin + 8, y, line)
        y -= 12
        if y < margin + 100:
            c.showPage()
            y = height - margin

    # Calculations block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y - 8, "2) Calculations & Results (step-by-step)")
    y -= 26
    c.setFont("Helvetica", 9)
    merged = st.session_state.get("last_calc") or calculated or {}
    if not merged:
        c.drawString(margin + 8, y, "No calculation available. Run calculation first to include detailed steps.")
        y -= 14
    else:
        # write key calculated outputs with short explanations
        for key, val in merged.items():
            # limit line length
            text_line = f"{key}: {val}"
            c.drawString(margin + 8, y, text_line)
            y -= 12
            if y < margin + 120:
                c.showPage()
                y = height - margin

    # Add drawing if available
    if last_figure_bytes:
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - margin, "3) Cross-section Drawing")
        img = Image.open(io.BytesIO(last_figure_bytes))
        # scale image to page width minus margins
        max_w = width - 2 * margin
        max_h = height - 2 * margin - 40
        img_w, img_h = img.size
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        disp_w = img_w * scale
        disp_h = img_h * scale
        img_reader = ImageReader(img)
        c.drawImage(img_reader, margin, height - margin - disp_h - 20, width=disp_w, height=disp_h)

    c.showPage()
    c.save()
    report_buf.seek(0)
    st.download_button("Download PDF report", data=report_buf, file_name="CEP_Report.pdf", mime="application/pdf")

st.markdown("---")
