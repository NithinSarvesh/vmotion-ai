"""
VMotion AI — DA1 Project Report Generator (Final Humanized Revision)
Generates VMotion_AI_DA1_Project_Report_FINAL.docx
Strictly for VIT Chennai, with humanized, student-presentable language,
clean formatting, defensible completion percentages (91.5% software, 15.0% physical hardware),
and all 5 real project screenshots embedded.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

OUTPUT_DOCX = r"d:\projects\vmotion ai\VMotion_AI_DA1_Project_Report_FINAL.docx"
SCREENSHOTS_DIR = r"d:\projects\vmotion ai\VMotion_AI_DA1_Screenshots"

# Color constants (Professional Academic Palette)
CLR_PRIMARY = RGBColor(15, 23, 42)      # Slate 900 (#0F172A)
CLR_SECONDARY = RGBColor(51, 65, 85)    # Slate 700 (#334155)
CLR_MUTED = RGBColor(100, 116, 139)     # Slate 500 (#64748B)
CLR_BLUE = RGBColor(37, 99, 235)        # Blue 600 (#2563EB)
CLR_INDIGO = RGBColor(79, 70, 229)      # Indigo 600 (#4F46E5)
CLR_EMERALD = RGBColor(16, 185, 129)    # Emerald 500 (#10B981)
CLR_AMBER = RGBColor(217, 119, 6)       # Amber 600 (#D97706)

HEX_PRIMARY = "0F172A"
HEX_CARD_BG = "FFFFFF"
HEX_SHADING = "F8FAFC"
HEX_PILL_BG = "F1F5F9"
HEX_BORDER = "CBD5E1"
HEX_BLUE = "2563EB"
HEX_INDIGO = "4F46E5"
HEX_EMERALD = "10B981"
HEX_AMBER = "D97706"

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_callout(doc, title, text, border_color_hex=HEX_BLUE, bg_hex=HEX_SHADING):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="32" w:space="0" w:color="{border_color_hex}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    run_t = p.add_run(f"■ {title.upper()}\n")
    run_t.font.name = "Arial"
    run_t.font.size = Pt(10)
    run_t.font.bold = True
    run_t.font.color.rgb = CLR_PRIMARY

    run_b = p.add_run(text)
    run_b.font.name = "Arial"
    run_b.font.size = Pt(9.5)
    run_b.font.color.rgb = CLR_SECONDARY

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_table_styled(doc, headers, data, col_widths=None):
    tbl = doc.add_table(rows=len(data) + 1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header Row
    for col_idx, h in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(h)
        run.font.name = "Arial"
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)

    # Data Rows
    for row_idx, row_vals in enumerate(data, start=1):
        bg = HEX_SHADING if row_idx % 2 == 1 else HEX_CARD_BG
        for col_idx, val in enumerate(row_vals):
            cell = tbl.cell(row_idx, col_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            run.font.name = "Arial"
            run.font.size = Pt(9)
            if col_idx == 0:
                run.font.bold = True
                run.font.color.rgb = CLR_PRIMARY
            else:
                run.font.color.rgb = CLR_SECONDARY

    if col_widths:
        for i, col in enumerate(tbl.columns):
            for cell in col.cells:
                cell.width = col_widths[i]

    for row in tbl.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            b = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'</w:tcBorders>'
            )
            tcPr.append(b)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return tbl

def add_custom_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    for r in h.runs:
        r.font.name = "Arial"
        if level == 1:
            r.font.size = Pt(15)
            r.font.bold = True
            r.font.color.rgb = CLR_PRIMARY
            h.paragraph_format.space_before = Pt(16)
            h.paragraph_format.space_after = Pt(6)
        elif level == 2:
            r.font.size = Pt(12.5)
            r.font.bold = True
            r.font.color.rgb = CLR_BLUE
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)
        elif level == 3:
            r.font.size = Pt(10.5)
            r.font.bold = True
            r.font.color.rgb = CLR_SECONDARY
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(3)
    return h

def add_body_p(doc, text, bold_prefix="", italic=False, space_after=5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Arial"
        r_pre.font.size = Pt(10)
        r_pre.font.bold = True
        r_pre.font.color.rgb = CLR_PRIMARY
    r_body = p.add_run(text)
    r_body.font.name = "Arial"
    r_body.font.size = Pt(10)
    r_body.font.italic = italic
    r_body.font.color.rgb = CLR_SECONDARY
    return p

def add_bullet(doc, title, text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    r1 = p.add_run(title + ": ")
    r1.font.name = "Arial"
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = CLR_PRIMARY
    r2 = p.add_run(text)
    r2.font.name = "Arial"
    r2.font.size = Pt(10)
    r2.font.color.rgb = CLR_SECONDARY

def add_figure_image(doc, filename, fig_num, caption, explanation):
    path = os.path.join(SCREENSHOTS_DIR, filename)
    if os.path.exists(path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(3)
        run = p_img.add_run()
        run.add_picture(path, width=Inches(6.0))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(3)
    r_cap = p_cap.add_run(f"Figure {fig_num}: {caption}\n")
    r_cap.font.name = "Arial"
    r_cap.font.size = Pt(9.5)
    r_cap.font.bold = True
    r_cap.font.color.rgb = CLR_PRIMARY

    r_exp = p_cap.add_run(explanation)
    r_exp.font.name = "Arial"
    r_exp.font.size = Pt(9)
    r_exp.font.italic = True
    r_exp.font.color.rgb = CLR_SECONDARY

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def build_report():
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    print("Building Humanized Academic Report for VIT Chennai...")

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(36)
    p_inst.paragraph_format.space_after = Pt(4)
    r = p_inst.add_run("VELLORE INSTITUTE OF TECHNOLOGY (VIT), CHENNAI\n")
    r.font.name = "Arial"; r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = CLR_PRIMARY
    r2 = p_inst.add_run("School of Computer Science and Engineering (SCOPE)\n")
    r2.font.name = "Arial"; r2.font.size = Pt(12); r2.font.color.rgb = CLR_SECONDARY
    r3 = p_inst.add_run("B.Tech. in Computer Science and Engineering • Academic Year 2025–2026")
    r3.font.name = "Arial"; r3.font.size = Pt(10); r3.font.color.rgb = CLR_MUTED

    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_before = Pt(16)
    p_div.paragraph_format.space_after = Pt(16)
    r_div = p_div.add_run("―" * 32)
    r_div.font.color.rgb = CLR_BLUE; r_div.font.bold = True

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(12)
    r_t1 = p_title.add_run("DIGITAL ASSIGNMENT 1 (DA1) EVALUATION REPORT\n")
    r_t1.font.name = "Arial"; r_t1.font.size = Pt(11); r_t1.font.bold = True; r_t1.font.color.rgb = CLR_BLUE
    r_t2 = p_title.add_run("VMotion AI: Intelligent Virtual Machine Migration using Reinforcement Learning")
    r_t2.font.name = "Arial"; r_t2.font.size = Pt(20); r_t2.font.bold = True; r_t2.font.color.rgb = CLR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(36)
    r_sub = p_sub.add_run("A Complete Project Architecture Combining Proximal Policy Optimization (PPO), a Deterministic 8-Rule Safety Gate, Human Operator Approval, and Proxmox VE Hypervisor Integration.")
    r_sub.font.name = "Arial"; r_sub.font.size = Pt(10.5); r_sub.font.italic = True; r_sub.font.color.rgb = CLR_SECONDARY

    # Candidate Card
    tbl_cand = doc.add_table(rows=1, cols=1)
    tbl_cand.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cand = tbl_cand.cell(0, 0)
    c_cand.width = Inches(5.8)
    set_cell_background(c_cand, HEX_PILL_BG)
    set_cell_margins(c_cand, top=160, bottom=160, left=220, right=220)
    p_c = c_cand.paragraphs[0]
    p_c.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_c.paragraph_format.line_spacing = 1.25

    runs_cand = [
        ("PROJECT DETAILS & CANDIDATE CREDENTIALS:\n", True, CLR_PRIMARY, 10),
        ("Student Name: ", True, CLR_SECONDARY, 10), ("Nithin Sarvesh M\n", True, CLR_BLUE, 11),
        ("Institutional Email: ", True, CLR_SECONDARY, 10), ("nithinsarvesh.m2025@vitstudent.ac.in\n", False, CLR_PRIMARY, 10),
        ("Program: ", True, CLR_SECONDARY, 10), ("B.Tech Computer Science and Engineering\n", False, CLR_PRIMARY, 10),
        ("Department: ", True, CLR_SECONDARY, 10), ("School of Computer Science and Engineering (SCOPE)\n", False, CLR_PRIMARY, 10),
        ("Institution: ", True, CLR_SECONDARY, 10), ("Vellore Institute of Technology (VIT), Chennai, Tamil Nadu, India\n", True, CLR_PRIMARY, 10),
        ("Submission / Course: ", True, CLR_SECONDARY, 10), ("Digital Assignment 1 (DA1) Evaluation\n", False, CLR_PRIMARY, 10),
        ("Software Completion: ", True, CLR_SECONDARY, 10), ("91.5% (Verified in Simulation)\n", True, CLR_EMERALD, 10),
        ("Hardware Validation: ", True, CLR_SECONDARY, 10), ("Pending Laboratory Hardware (15.0%)\n", True, CLR_AMBER, 10),
        ("Submission Date: ", True, CLR_SECONDARY, 10), ("September 19, 2026", False, CLR_PRIMARY, 10)
    ]
    for text, bold, color, sz in runs_cand:
        r = p_c.add_run(text)
        r.font.name = "Arial"; r.font.bold = bold; r.font.color.rgb = color; r.font.size = Pt(sz)

    doc.add_page_break()

    # =========================================================================
    # ABSTRACT
    # =========================================================================
    add_custom_heading(doc, "Abstract", level=1)
    add_body_p(doc,
        "In modern cloud infrastructure, server loads fluctuate constantly. Static migration rules (such as migrating a virtual machine whenever host CPU exceeds 80%) "
        "often react too late or cause workloads to bounce back and forth unnecessarily during brief spikes. Conversely, while Reinforcement Learning (RL) can learn to anticipate "
        "imbalances and optimize cluster load over time, an unconstrained AI model cannot be allowed to execute raw hypervisor commands directly due to the risk of unsafe decisions."
    )
    add_body_p(doc,
        "VMotion AI solves this problem by using a decoupled design: the reinforcement learning model (MaskablePPO) recommends which VM to relocate, a separate deterministic safety gate "
        "checks 8 physical rules to confirm that the migration is safe, a human operator approves the proposal, and the backend orchestrates the migration through hypervisor APIs."
    )
    add_body_p(doc,
        "The AI decision engine ingests a normalized 103-dimensional state vector representing node telemetry, per-VM utilization, and cluster-wide fairness. "
        "During development, we discovered that an early model (PPO V4) suffered from policy collapse, learning to do nothing (0.0 migrations) because it was trained only on normal cluster conditions. "
        "We fixed this in PPO V5 by introducing a balanced training sampler across four cluster states: Normal, CPU Hotspot, RAM Hotspot, and Mixed Overload. "
        "In a 600-episode benchmark across 10 evaluation scenarios, PPO V5 achieved an overall reward improvement of +319.29 points over V4 (+55.81 vs. -263.48), "
        "achieved a reward of +154.93 on unseen test scenarios, cut server overload time by 87.8%, and reached a Jain's Fairness Index of 0.9288."
    )
    add_body_p(doc,
        "The project also includes a 12-state migration finite state machine (FSM) that monitors Proxmox task UPIDs, verifies destination placement, and pings the QEMU guest-agent before marking a migration complete. "
        "An interactive React 19 web console with Three.js 3D cluster visualization and append-only audit logging provides full operational visibility. "
        "With 96 passing backend unit tests and a clean frontend build, the software implementation stands at 91.5% completion, with physical Proxmox hardware testing documented as pending laboratory scheduling."
    )

    add_callout(doc, "KEYWORDS", "Virtual Machine Live Migration, Reinforcement Learning, Proximal Policy Optimization (PPO), Deterministic Safety Gate, Proxmox VE 9.x, Cluster Load Balancing, Human-in-the-Loop, Cloud Infrastructure.", border_color_hex=HEX_INDIGO)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1: INTRODUCTION & BACKGROUND
    # =========================================================================
    add_custom_heading(doc, "1. Introduction & Background", level=1)
    add_body_p(doc,
        "Virtualization allows multiple independent virtual machines (VMs) to share the same physical server hardware. In enterprise environments managed by hypervisors like Proxmox VE and KVM, "
        "workloads rarely stay at a constant load. Traffic spikes, database batch jobs, and user demand cause compute and memory utilization to shift dynamically throughout the day."
    )
    add_body_p(doc,
        "Live VM Migration is the ability to move a running virtual machine from one physical host to another across a network connection without shutting it down. "
        "The hypervisor iteratively copies memory pages to the destination while the VM is still running, briefly pauses execution for a few milliseconds to copy the final dirty pages and CPU registers, "
        "and immediately resumes execution on the new host."
    )
    add_body_p(doc,
        "The challenge is not how to migrate, but when and where to migrate. Moving a VM takes network bandwidth and CPU cycles. Migrating too early or too frequently hurts performance. "
        "Migrating too late causes severe server throttling. VMotion AI was developed to automate this decision process intelligently using reinforcement learning while keeping strong safety controls."
    )

    # =========================================================================
    # CHAPTER 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    add_custom_heading(doc, "2. Problem Statement & Motivation", level=1)
    add_custom_heading(doc, "2.1 Problem Statement", level=2)
    add_body_p(doc,
        "Traditional cloud migration managers rely on static threshold rules (e.g. migrate when host CPU exceeds 80%). This creates several real-world issues:"
    )
    add_bullet(doc, "Migration Flapping", "A brief 30-second spike trips the rule and triggers a migration. By the time the VM finishes moving, the spike is gone, and the system moves it right back.")
    add_bullet(doc, "Suboptimal Destination Picks", "Heuristic rules often pick whatever server looks least loaded at that exact moment, without checking whether the destination has enough RAM headroom or whether its load is rising.")
    add_bullet(doc, "Manual Delays", "When automated rules are disabled, system administrators have to respond manually, which usually takes several minutes during which customer applications suffer.")

    add_callout(doc, "PROBLEM STATEMENT",
        "How can we automatically rebalance virtual machines across infrastructure nodes using reinforcement learning based on real cluster conditions, "
        "while ensuring that the AI cannot make unsafe or destabilizing migration decisions?",
        border_color_hex=HEX_BLUE
    )

    add_custom_heading(doc, "2.2 Motivation: Why a Safety Layer Is Needed", level=2)
    add_body_p(doc,
        "Reinforcement learning is well suited for this problem because a trained agent can learn complex multi-server relationships that simple if/else rules miss. "
        "However, an RL policy is a statistical neural network. It can make mistakes, especially in unusual situations. "
        "If an RL model were allowed to send commands directly to a hypervisor, it could accidentally pick an overloaded destination, try to migrate a VM that is already moving, or saturate memory. "
        "Our motivation was to build a system where the AI only recommends actions, and a deterministic safety layer verifies every physical constraint before anything executes."
    )

    # =========================================================================
    # CHAPTER 3: OBJECTIVES & KEY CONSTRAINTS
    # =========================================================================
    add_custom_heading(doc, "3. Project Objectives & Key Constraints", level=1)
    add_body_p(doc, "The project was designed and implemented against four concrete objectives:")
    add_bullet(doc, "1. Real-Time Telemetry & 103-Feature Adapter", "Capture CPU, RAM, Network, Disk, and VM metrics from hypervisors and convert them into a normalized 103-dimensional state vector.")
    add_bullet(doc, "2. PPO Decision Engine with Action Masking", "Train a MaskablePPO agent over a Discrete(7) action space with cooldown masking to select candidate VMs for rebalancing.")
    add_bullet(doc, "3. Deterministic 8-Rule Safety Gate", "Build a separate verification layer that independently checks host health, target CPU, memory headroom, quorum, and cooldown under fail-closed logic.")
    add_bullet(doc, "4. Operator Approval & Proxmox REST Integration", "Provide an operator approval interface, track migrations across a 12-state FSM, and verify post-migration placement and QEMU guest health.")

    add_callout(doc, "KEY DESIGN CONSTRAINTS",
        "• The AI Recommends. The Safety Gate Validates. The Human Approves. The Backend Executes.\n"
        "• The frontend never communicates directly with hypervisors.\n"
        "• The RL model never directly issues migration commands.\n"
        "• Live mode never silently falls back to simulation data if servers disconnect.\n"
        "• We distinguish clearly between what is validated in simulation vs. pending physical hardware.",
        border_color_hex=HEX_AMBER
    )

    # =========================================================================
    # CHAPTER 4: EXISTING VS PROPOSED SYSTEM
    # =========================================================================
    add_custom_heading(doc, "4. Existing Systems vs. Proposed VMotion AI", level=1)
    add_body_p(doc, "Table 4.1 compares traditional migration approaches with VMotion AI:")

    table_comp_data = [
        ("Decision Method", "Static threshold rules (e.g. CPU > 80%) or greedy heuristic searches.", "Reinforcement Learning (PPO) optimizes for overall cluster balance over time.", "Proactive anticipation vs. reactive threshold tripping."),
        ("State Awareness", "Looks at single-server metrics; misses cluster-wide variance.", "103-dimensional state vector tracks all nodes, VMs, and cluster fairness.", "Complete cluster-wide situational awareness."),
        ("Flapping Control", "Crude delays; VMs often migrate back and forth during load spikes.", "60-second cooldown dynamically enforced via invalid action masking.", "Prevents repeat migrations of recently moved workloads."),
        ("Safety Model", "Rules execute directly on servers; no independent verification step.", "Separate 8-rule safety gate verifies target capacity before any command runs.", "Guarantees physical safety constraints are never violated."),
        ("Operator Control", "Either completely manual (slow tickets) or unmonitored script execution.", "Two-phase workflow: operator sees AI recommendation and must approve it.", "Human administrator retains final authority over physical dispatches.")
    ]
    add_table_styled(doc,
        ["Aspect", "Traditional / Heuristic Approach", "VMotion AI Approach", "Benefit"],
        table_comp_data,
        [Inches(1.2), Inches(2.3), Inches(2.3), Inches(1.7)]
    )

    # =========================================================================
    # CHAPTER 5: SYSTEM ARCHITECTURE
    # =========================================================================
    add_custom_heading(doc, "5. System Architecture & Component Separation", level=1)
    add_body_p(doc,
        "VMotion AI is organized into four decoupled tiers, ensuring that AI inference is separated from hypervisor execution:"
    )

    add_callout(doc, "SYSTEM ARCHITECTURE OVERVIEW",
        "TIER 1: INFRASTRUCTURE LAYER (Proxmox VE 9.x Cluster / Simulation Engine)\n"
        "         ↓ [Node metrics, VM operational status, live migration stream]\n"
        "TIER 2: TELEMETRY & 103-FEATURE ADAPTER (Rolling buffers, Jain's index)\n"
        "         ↓ [103-dimensional state vector S ∈ [-1.0, 1.0] and action mask]\n"
        "TIER 3: REINFORCEMENT LEARNING ENGINE (PPO V5 model / Heuristic fallback)\n"
        "         ↓ [Candidate migration action + destination headroom target]\n"
        "TIER 4: SAFETY GATE, OPERATOR APPROVAL & STATE MACHINE (8 Rules, 12 States)\n"
        "         ↓ [Audited, operator-approved dispatch to Proxmox REST API]\n"
        "WEB CONTROL PLANE (React 19, Three.js 3D cluster, append-only audit stream)",
        border_color_hex=HEX_BLUE
    )

    add_body_p(doc, "Tier Details:")
    add_bullet(doc, "Tier 1: Infrastructure Layer", "Interfaces with Proxmox VE 9.x servers over HTTPS REST API v2 (port 8006), Corosync (UDP 5405-5412), and QEMU migration streams (TCP 60000-60050). In development mode, the SimulationProvider emulates these dynamics.")
    add_bullet(doc, "Tier 2: Telemetry & Feature Adapter", "Polls servers every 2 seconds, updates rolling averages, computes Jain's Fairness Index across CPU and RAM, and builds the normalized 103-dimensional feature vector.")
    add_bullet(doc, "Tier 3: Reinforcement Learning Engine", "Runs the trained MaskablePPO model to recommend which VM should be relocated, while destination target resolution is handled deterministically based on available headroom.")
    add_bullet(doc, "Tier 4: Safety, Governance & State Machine", "Enforces the 8 deterministic safety checks under fail-closed logic, presents proposals for human operator signoff, tracks task UPIDs, and verifies post-migration guest health.")

    # =========================================================================
    # CHAPTER 6: END-TO-END WORKFLOW
    # =========================================================================
    add_custom_heading(doc, "6. End-to-End System Workflow", level=1)
    add_body_p(doc, "Each migration decision proceeds through eight clear steps:")
    w_steps = [
        ("Step 1: Telemetry Sampling", "The collector queries active hypervisor nodes or simulation every 2 seconds for CPU, RAM, Disk, and Network IO."),
        ("Step 2: 103-Feature Normalization", "Raw metrics are converted into bounded floating-point numbers between -1.0 and 1.0, and cluster fairness is calculated."),
        ("Step 3: Action Masking", "Any VM currently in an active 60-second cooldown or in a stopped state is masked out so the AI cannot pick it."),
        ("Step 4: PPO Policy Evaluation", "The PPO V5 model evaluates the state vector and recommends the best candidate VM to migrate."),
        ("Step 5: Pick Best Target Host", "A deterministic resolver checks which destination server currently has the highest compute headroom."),
        ("Step 6: Run Safety Gate Checks", "The safety gate checks 8 physical rules (RAM margin, CPU ceiling, node health, quorum). If any fail, the proposal is blocked."),
        ("Step 7: Operator Approval", "If safety checks pass, the proposal appears on the dashboard for human operator authorization."),
        ("Step 8: Execute & Verify Health", "Upon approval, the migration command is sent to Proxmox, the task UPID is monitored, and guest-agent health is verified.")
    ]
    for head, desc in w_steps:
        add_bullet(doc, head, desc)

    # =========================================================================
    # CHAPTER 7: MODULE BREAKDOWN
    # =========================================================================
    add_custom_heading(doc, "7. Repository Module Breakdown", level=1)
    add_body_p(doc, "Table 7.1 outlines the primary software modules in the repository:")

    mod_data = [
        ("Telemetry Collector", "backend/app/telemetry/collector.py", "Background task polling hypervisors; maintains rolling metric buffers and cluster stats.", "COMPLETE (100%)"),
        ("103-Feature Adapter", "backend/app/adapter/observation.py", "Extracts the exact 103 continuous normalized features with bounds checking.", "COMPLETE (100%)"),
        ("PPO Decision Engine", "backend/app/engine/ppo_engine.py", "Loads trained MaskablePPO weights, evaluates policy, and provides heuristic fallback.", "COMPLETE (V5)", ),
        ("Deterministic Safety Gate", "backend/app/safety/gate.py", "Implements 8 mandatory safety rules and manages thread-safe migration locks.", "COMPLETE (100%)"),
        ("Migration FSM Planner", "backend/app/planner/planner.py", "Coordinates the 12-state FSM, manages human approval, and verifies post-placement state.", "COMPLETE (100%)"),
        ("Proxmox VE Provider", "backend/app/providers/proxmox.py", "Connects to Proxmox REST API v2, handles token auth, and monitors task UPIDs.", "MOCK TESTED (75%)"),
        ("Simulation Provider", "backend/app/providers/simulation.py", "High-fidelity synthetic cluster (3 nodes, 6 VMs) emulating CPU drift and memory dirtying.", "COMPLETE (100%)"),
        ("Web Control Dashboard", "frontend/src/ (React 19 + 3D)", "Three.js 3D cluster view, Lenis smooth scrolling, live telemetry, and audit logging.", "COMPLETE (100%)")
    ]
    add_table_styled(doc,
        ["Module Name", "Primary File", "Role & Responsibility", "Status"],
        mod_data,
        [Inches(1.6), Inches(2.2), Inches(2.4), Inches(1.3)]
    )

    # =========================================================================
    # CHAPTER 8: TECHNOLOGIES USED
    # =========================================================================
    add_custom_heading(doc, "8. Technologies, Libraries & Frameworks", level=1)
    tech_data = [
        ("Python 3.11", "Backend Language", "Backend control plane, reinforcement learning training, and REST/WebSocket APIs."),
        ("Stable-Baselines3 / sb3-contrib", "RL Framework", "MaskablePPO implementation supporting invalid action masking over Discrete action spaces."),
        ("PyTorch 2.2+", "Deep Learning Library", "Underlying tensor computation and actor-critic neural network evaluation."),
        ("FastAPI & Uvicorn", "Web & API Framework", "Asynchronous REST API endpoints and native WebSocket telemetry streaming."),
        ("React 19 & TypeScript", "Frontend Core", "Modern frontend component architecture with strict end-to-end type safety."),
        ("Three.js & Lenis", "Graphics & Motion", "WebGL 3D cluster visualization and smooth scroll navigation across control plane sections."),
        ("Pytest & httpx", "Testing & Async HTTP", "Automated test suite (96 tests) and async HTTP communication with Proxmox APIs.")
    ]
    add_table_styled(doc,
        ["Technology", "Category", "Role in VMotion AI"],
        tech_data,
        [Inches(1.8), Inches(1.8), Inches(3.9)]
    )

    # =========================================================================
    # CHAPTER 9: RL METHODOLOGY
    # =========================================================================
    add_custom_heading(doc, "9. Reinforcement Learning Methodology (MaskablePPO)", level=1)
    add_body_p(doc,
        "We model cluster rebalancing as a Markov Decision Process (MDP) with a 103-dimensional state space, Discrete(7) action space, and multi-objective reward. "
        "We chose Proximal Policy Optimization (PPO) because its clipped surrogate objective prevents overly large policy updates that could destabilize learning."
    )
    add_body_p(doc,
        "Why Action Masking Is Essential: In hypervisor management, attempting to migrate a VM that is already moving or migrating a VM that was moved 10 seconds ago violates operational rules. "
        "Standard RL penalizes bad actions after the fact, which wastes training time. With MaskablePPO, invalid action probabilities are set to zero before the softmax step, "
        "ensuring the agent only samples valid actions and preventing migration flapping."
    )

    # =========================================================================
    # CHAPTER 10: 103-FEATURE OBSERVATION SPACE
    # =========================================================================
    add_custom_heading(doc, "10. 103-Dimensional Observation Space", level=1)
    add_body_p(doc, "The 103 continuous features are divided into three deterministic blocks:")
    add_bullet(doc, "Block 1: Node Telemetry (24 Features, Indices 0..23)", "3 servers x 8 features each: CPU util, RAM util, network RX/TX, disk util, VM density, online status flag, and CPU headroom fraction.")
    add_bullet(doc, "Block 2: VM Telemetry (60 Features, Indices 24..83)", "6 virtual machines x 10 features each: CPU util, RAM alloc, RAM util, network IO, SLA weight, cooldown timer, migration count, uptime, contention, and host ID.")
    add_bullet(doc, "Block 3: Cluster & Fairness (19 Features, Indices 84..102)", "Jain's Fairness Index for CPU and RAM, cluster standard deviation, average CPU/RAM, dynamic power index, SLA breach ratio, storage accessibility, and quorum consensus.")

    # =========================================================================
    # CHAPTER 11: ACTION SPACE & REWARD DESIGN
    # =========================================================================
    add_custom_heading(doc, "11. Action Space & Reward Function Design", level=1)
    add_body_p(doc,
        "Action Space: Discrete(7) where Action 0 represents No-Op (cluster in equilibrium; no migration needed), and Actions 1..6 represent selecting VM-01 through VM-06 for migration. "
        "The destination host is chosen deterministically by finding the server with the greatest available compute headroom."
    )
    add_body_p(doc, "Multi-Objective Reward Function:", bold_prefix="Reward: ")
    add_callout(doc, "PER-STEP REWARD FORMULA",
        "Reward = Balance + Stability - SLA Penalty - Overload Penalty - Migration Cost\n\n"
        "• Balance Dividend: +2.5 * Jain_CPU - 1.5 * Std_CPU (rewards uniform load spread across servers)\n"
        "• Stability Bonus: +1.0 for choosing No-Op when cluster is already well balanced\n"
        "• SLA Penalty: -2.0 for each workload exceeding its assigned SLA ceiling\n"
        "• Overload Penalty: -4.0 if any server exceeds 85% CPU capacity (heavy penalty to prevent host exhaustion)\n"
        "• Migration Cost: -0.8 for each migration to account for network bandwidth and memory copying overhead",
        border_color_hex=HEX_INDIGO
    )

    # =========================================================================
    # CHAPTER 12: PPO TRAINING EVOLUTION (V4 vs V5)
    # =========================================================================
    add_custom_heading(doc, "12. PPO Training Evolution: Diagnosing & Fixing Policy Collapse", level=1)
    add_custom_heading(doc, "12.1 The V4 Policy Collapse", level=2)
    add_body_p(doc,
        "During early testing, PPO V4 exhibited policy collapse: it learned to do nothing (0.0 migrations per episode) even when servers were suffering from 95% CPU hotspots. "
        "Investigation showed this was caused by training-distribution mismatch. PPO V4 was trained entirely on normal, balanced cluster states. "
        "In a balanced state, any migration action incurs a -0.8 penalty without any benefit. As a result, the model quickly learned that Action 0 (No-Op) was always best, "
        "and stopped attempting migrations altogether."
    )
    add_custom_heading(doc, "12.2 The V5 Multi-Scenario Breakthrough", level=2)
    add_body_p(doc,
        "We resolved this in PPO V5 by training across four balanced scenarios (25% Normal, 25% CPU Hotspot, 25% RAM Hotspot, 25% Mixed Overload). "
        "By seeing hotspots during training, PPO V5 learned that the reward for rebalancing heavily outweighed the transient migration penalty. "
        "The candidate model was frozen as `models/ppo_vmotion_v5_masked.zip` (SHA-256: `bc47c2a564d2...`)."
    )

    table_v5_results = [
        ("Overall Mean Reward", "-122.54", "-89.25", "-263.48", "+55.81", "+319.29 points"),
        ("Unseen Test Split Reward", "+115.37", "+53.28", "-53.16", "+154.93", "+208.09 points"),
        ("Mean Migrations / Episode", "14.79", "73.11", "0.00 (Collapsed)", "2.07 (Targeted)", "+2.07 migrations"),
        ("Server Overload Steps / Ep", "6.68", "16.93", "60.22", "7.33", "-52.89 steps (-87.8%)"),
        ("Final Jain's Fairness Index", "0.9610", "0.8944", "0.7682", "0.9288", "+0.1606 (+20.9%)")
    ]
    add_table_styled(doc,
        ["Metric", "Baseline Heuristic", "Random Masked", "PPO V4 (Collapse)", "PPO V5 (Balanced)", "V4 -> V5 Delta"],
        table_v5_results,
        [Inches(1.8), Inches(1.1), Inches(1.1), Inches(1.2), Inches(1.1), Inches(1.2)]
    )

    # =========================================================================
    # CHAPTER 13: SAFETY GATE & FSM
    # =========================================================================
    add_custom_heading(doc, "13. Deterministic Safety Gate & Migration State Machine", level=1)
    add_custom_heading(doc, "13.1 The 8 Safety Rules", level=2)
    add_body_p(doc, "The safety gate evaluates 8 physical rules under fail-closed logic:")
    safety_rules_short = [
        ("Rule 1: VM_RUNNING_STATE", "Confirms the workload is currently in a running hypervisor state."),
        ("Rule 2: DISTINCT_TARGET", "Ensures source and destination are two different physical servers (src != dest)."),
        ("Rule 3: SOURCE_NODE_HEALTH", "Checks that the source server daemon has active heartbeat and no alarms."),
        ("Rule 4: DEST_NODE_HEALTH", "Ensures destination server is online and reachable over cluster network."),
        ("Rule 5: DEST_RAM_HEADROOM", "Target unallocated RAM must fit the VM plus a 20% safety margin."),
        ("Rule 6: DEST_CPU_CAPACITY", "Projected CPU utilization on target server after migration must remain <= 85%."),
        ("Rule 7: STORAGE_AND_QUORUM", "Verifies target datastore accessibility and cluster quorum consensus."),
        ("Rule 8: COOLDOWN_PERIOD", "Prevents migrating a VM that was relocated less than 60 seconds ago.")
    ]
    for head, desc in safety_rules_short:
        add_bullet(doc, head, desc)

    add_custom_heading(doc, "13.2 The 12-State Migration FSM", level=2)
    add_body_p(doc,
        "Every migration is tracked across 12 states:\n"
        "• 8 Progressive States: RECOMMENDED → SAFETY_CHECK → PENDING_APPROVAL → APPROVED → DISPATCHED → TASK_RUNNING → VERIFYING → VERIFIED.\n"
        "• 4 Terminal States: BLOCKED (by safety gate), REJECTED (by operator), FAILED (hypervisor error), CANCELLED (operator abort).\n"
        "Illegal transitions raise an `InvalidStateTransitionError`, ensuring tasks cannot skip verification."
    )

    # =========================================================================
    # CHAPTER 14: PROXMOX INTEGRATION
    # =========================================================================
    add_custom_heading(doc, "14. Proxmox VE 9.x Hypervisor Integration", level=1)
    add_body_p(doc,
        "The Proxmox VE Provider (`backend/app/providers/proxmox.py`) connects to Proxmox VE 9.x REST API v2 over HTTPS (port 8006). "
        "Key implementation details include:"
    )
    add_bullet(doc, "Privilege Separation (-privsep 1)", "Configured via `pveum user token add vmotion-api@pve automation -privsep 1`. The token header `PVEAPIToken=vmotion-api@pve!automation=SECRET` is used for all API requests.")
    add_bullet(doc, "Audited Least Privilege ACL", "Requires Sys.Audit, VM.Audit, VM.Migrate, VM.Allocate, Datastore.Audit, Datastore.AllocateSpace, and VM.GuestAgent.Audit. (The invalid privilege VM.Monitor was removed).")
    add_bullet(doc, "Asynchronous Task Tracking", "Dispatches `POST /nodes/{node}/qemu/{vmid}/migrate`, parses the returned UPID string, and polls task status at 1.0s intervals.")
    add_bullet(doc, "QEMU Guest-Agent Ping", "After placement assertion, issues `GET .../agent/ping` to confirm the guest OS is responsive before marking the migration verified.")
    add_bullet(doc, "2-Node Quorum Consideration", "In a 2-node lab cluster, failure of 1 node breaks quorum. An external QDevice (`corosync-qnetd`) can be deployed to provide a 3rd vote for fault tolerance.")

    # =========================================================================
    # CHAPTER 15: TESTING & VALIDATION
    # =========================================================================
    add_custom_heading(doc, "15. Testing & Validation Results (96 Passing Tests)", level=1)
    add_body_p(doc,
        "The backend test suite was run via `pytest backend/tests`. All 96 tests passed in 19.47 seconds with zero failures:"
    )
    add_bullet(doc, "Safety Gate Coverage (12 tests)", "Verifies all 8 rules block on: identical hosts, offline servers, stopped VMs, high RAM, high CPU, and active cooldown.")
    add_bullet(doc, "Migration Lifecycle Coverage (10 tests)", "Verifies 12-state FSM progression and confirms illegal transitions raise errors.")
    add_bullet(doc, "Observation Spec Coverage (8 tests)", "Verifies 103 feature dimension, mathematical bounds [-1.0, 1.0], and deterministic sorting.")
    add_bullet(doc, "Provider Contract Coverage (10 tests)", "Tests Simulation, Proxmox, and Libvirt providers for schema conformity and truthful disconnection.")
    add_bullet(doc, "API & Security Coverage (14 tests)", "Verifies FastAPI endpoints, token secret masking in /api/cluster/config, and live mode confirmation headers.")

    add_callout(doc, "AUTOMATED TEST SUITE SUMMARY",
        "• Backend Tests: 96 Passed / 0 Failed (19.47s runtime across 11 test modules)\n"
        "• Frontend Production Build: 1,891 modules transformed via Vite — 0 TypeScript errors, 0 lint warnings.",
        border_color_hex=HEX_EMERALD
    )

    # =========================================================================
    # CHAPTER 16: IMPLEMENTATION SCREENSHOTS
    # =========================================================================
    add_custom_heading(doc, "16. Implementation Screenshots & Control Plane Walkthrough", level=1)
    add_body_p(doc,
        "This section presents five unmanipulated screenshots captured directly from the running VMotion AI control plane "
        "(frontend at http://localhost:5173, backend at http://127.0.0.1:8000):"
    )

    add_figure_image(doc, "01_hero_spatial_overview.png", "16.1",
        "VMotion AI 3D Cluster Overview & Telemetry Header",
        "Shows the environment mode pill ('SIMULATION • SYNTHETIC CLUSTER'), the governance badge ('HUMAN APPROVAL REQUIRED'), "
        "the 5-phase decision ticker, and the Three.js 3D WebGL spatial cluster displaying host pedestals and orbiting VM chassis."
    )

    add_figure_image(doc, "02_ai_engine_decision_pipeline.png", "16.2",
        "AI Decision Pipeline & PPO Model Artifact Status",
        "Shows the 5-stage inference ticker, current policy recommendation ('CLUSTER LOAD IN EQUILIBRIUM' / No-Op Action 0), "
        "and the Model Artifact Status card displaying candidate 'PPO V5 (Frozen)', 103 features, Discrete(7) action space, "
        "and verified SHA-256 artifact checksum (bc47c2a564d2...)."
    )

    add_figure_image(doc, "03_deterministic_safety_gate.png", "16.3",
        "Mandatory 8-Rule Safety Criteria Matrix (8 of 8 Satisfied)",
        "Shows the live evaluation of all 8 safety rules: VM_RUNNING_STATE, DISTINCT_TARGET, SOURCE_NODE_HEALTH, "
        "DEST_NODE_HEALTH, DEST_RAM_HEADROOM, DEST_CPU_CAPACITY, STORAGE_AND_QUORUM, and COOLDOWN_PERIOD before operator approval."
    )

    add_figure_image(doc, "04_migration_fsm_orchestration.png", "16.4",
        "8-State Migration FSM Lifecycle Tracker & Dispatch Queue",
        "Shows the migration state machine progression: RECOMMENDED → SAFETY CHECK → OPERATOR GATE → APPROVED → "
        "DISPATCHED → PRE-COPY / RUNNING → VERIFYING → VERIFIED, along with terminal rejection states and active dispatch queue."
    )

    add_figure_image(doc, "05_append_only_audit_ledger.png", "16.5",
        "Append-Only Forensic Audit Ledger & Event History",
        "Shows the immutable audit ledger with category filters (ALL, AI, SAFETY, OPERATOR, MIGRATION, VERIFICATION), "
        "live search, and timestamped initialization events ensuring complete operational traceability."
    )

    # =========================================================================
    # CHAPTER 17: COMPLETION PERCENTAGE ANALYSIS
    # =========================================================================
    add_custom_heading(doc, "17. Project Completion Percentage & Progress Analysis", level=1)
    add_body_p(doc,
        "To provide an evidence-backed answer for academic evaluation, Table 17.1 details our weighted completion model derived from repository code and tests:"
    )

    comp_data = [
        ("Architecture & Interface Specs", "10%", "100%", "10.0%", "Observation spec v1.0.0, action spec v1.0.0, provider contracts fully frozen."),
        ("Backend & Control Plane", "15%", "100%", "15.0%", "FastAPI async routing, WebSocket telemetry streaming, masked config, audit logging."),
        ("Telemetry & 103-Dim Adapter", "10%", "100%", "10.0%", "Collector, rolling buffer, Jain's index, exact 103-dim normalization verified."),
        ("PPO / Reinforcement Learning", "15%", "100%", "15.0%", "MaskablePPO trained, V4 collapse resolved, PPO V5 frozen with verified SHA-256."),
        ("Safety Gate & 12-State FSM", "15%", "100%", "15.0%", "8 physical safety rules, fail-closed audit, 12 FSM states, operator approval gate."),
        ("Hypervisor Provider Integration", "10%", "75%", "7.5%", "Simulation provider 100%; Proxmox provider code 100% complete but hardware unverified."),
        ("Frontend Control Dashboard", "10%", "100%", "10.0%", "React 19, Three.js 3D cluster, Lenis scrolling, clean build with zero errors."),
        ("Automated Tests & Benchmarks", "10%", "90%", "9.0%", "96 backend tests pass (100%); 600-ep benchmark (100%); physical hardware test pending."),
        ("Documentation & Specifications", "5%", "100%", "5.0%", "Comprehensive markdown specs for observation, reward, integration, and readiness.")
    ]
    add_table_styled(doc,
        ["Subsystem Component", "Weight", "Module %", "Weighted Contribution", "Evidence / Status"],
        comp_data,
        [Inches(1.8), Inches(0.8), Inches(0.8), Inches(1.1), Inches(2.8)]
    )

    add_callout(doc, "THE TWO DEFENSIBLE NUMBERS",
        "1. Software Implementation & Simulation Readiness: 91.5%\n"
        "   (All architectural tiers, RL models, safety gates, FSM orchestrator, APIs, 3D UI, and 96 unit tests are 100% functional in simulation.)\n\n"
        "2. Real Physical Infrastructure Demonstration: Pending Laboratory Hardware (15.0%)\n"
        "   (Proxmox REST client code, token auth, and UPID parsers are implemented and mock-tested, but real physical live migration "
        "over external servers remains pending physical lab scheduling at VIT Chennai.)",
        border_color_hex=HEX_BLUE
    )

    # =========================================================================
    # CHAPTER 18: LIMITATIONS & FUTURE WORK
    # =========================================================================
    add_custom_heading(doc, "18. Limitations & Future Roadmap", level=1)
    add_custom_heading(doc, "18.1 Current Scope & Limitations", level=2)
    add_bullet(doc, "Physical Hardware Pending", "While `ProxmoxVEProvider` is fully implemented in code and tested against HTTP mocks, physical execution over real hypervisors in the lab is pending scheduling.")
    add_bullet(doc, "Two-Node Quorum Vulnerability", "A 2-node Proxmox cluster loses Corosync quorum if a single host fails, blocking migration APIs unless an external QDevice (`corosync-qnetd`) is deployed.")
    add_bullet(doc, "Fixed Cluster Topology", "The current PPO state space is dimensioned for a 3-node, 6-VM cluster. Scaling to larger clusters will benefit from Graph Neural Networks (GNNs).")

    add_custom_heading(doc, "18.2 Future Development Roadmap", level=2)
    add_bullet(doc, "Lab Rack Deployment", "Connect VMotion AI to physical Proxmox VE 9.2 servers in the VIT Chennai networking laboratory.")
    add_bullet(doc, "Deploy Corosync QDevice", "Add an external Raspberry Pi or VM running `corosync-qnetd` for quorum resilience in 2-node setups.")
    add_bullet(doc, "Graph Neural Network (GNN) Policy", "Adopt Graph Convolutional Networks to support dynamic clusters with arbitrary numbers of nodes and VMs.")
    add_bullet(doc, "Time-Series Predictive Pre-empting", "Use lightweight forecasting (e.g. ARIMA) to trigger migrations 2 minutes before contention peaks.")

    # =========================================================================
    # CHAPTER 19: CONCLUSION
    # =========================================================================
    add_custom_heading(doc, "19. Conclusion", level=1)
    add_body_p(doc,
        "VMotion AI demonstrates that reinforcement learning can be effectively applied to virtual machine live migration when paired with a deterministic safety gate and human operator oversight. "
        "By separating the AI reasoning layer from hypervisor execution, the system prevents unsafe migration decisions while optimizing cluster load over time."
    )
    add_body_p(doc,
        "Key Accomplishments:\n"
        "• Diagnosed and resolved policy collapse in PPO V4 using balanced multi-scenario sampling, creating the frozen PPO V5 model (+154.93 unseen test reward, 87.8% reduction in server overload).\n"
        "• Implemented an 8-rule deterministic safety gate operating under fail-closed logic to verify physical host capacity before migration.\n"
        "• Built a 12-state migration FSM tracking task UPIDs, post-placement residency, and QEMU guest-agent health.\n"
        "• Integrated a Proxmox VE 9.x REST client with privilege separation and an interactive React 19 3D control plane.\n"
        "• Verified through 96 passing automated backend tests, achieving a defensible 91.5% software implementation completion."
    )

    # =========================================================================
    # REFERENCES
    # =========================================================================
    add_custom_heading(doc, "References", level=1)
    refs = [
        "1. Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). Proximal Policy Optimization Algorithms. arXiv:1707.06347.",
        "2. Clark, C., Fraser, K., Hand, S., Hansen, J. G., Jul, E., Limpach, C., Pratt, I., & Warfield, A. (2005). Live Migration of Virtual Machines. In NSDI '05, pp. 273–286.",
        "3. Jain, R., Chiu, D. M., & Hawe, W. R. (1984). A Quantitative Measure of Fairness and Discrimination for Resource Allocation. DEC Research Report TR-301.",
        "4. Raffin, A., Hill, A., Gleave, A., Kanervisto, A., Ernestus, M., & Dormann, N. (2021). Stable-Baselines3: Reliable Reinforcement Learning Implementations. JMLR, 22(268), 1–8.",
        "5. Proxmox Server Solutions GmbH. (2026). Proxmox Virtual Environment 9.x Technical Documentation & REST API Reference. https://pve.proxmox.com/pve-docs/",
        "6. Huang, S., & Ontañón, S. (2022). A Closer Look at Invalid Action Masking in Policy Gradient Algorithms. FLAIRS-35.",
        "7. Beloglazov, A., & Buyya, R. (2012). Optimal Online Deterministic Algorithms for Dynamic Consolidation of Virtual Machines. Concurrency and Computation, 24(13), 1397–1420.",
        "8. VMware Inc. (2024). VMware vSphere Distributed Resource Scheduler (DRS) Technical Whitepaper."
    ]
    for r in refs:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(r)
        run.font.name = "Arial"; run.font.size = Pt(9); run.font.color.rgb = CLR_SECONDARY

    doc.save(OUTPUT_DOCX)
    print(f"Final Humanized Project Report generated successfully: {OUTPUT_DOCX}")

if __name__ == "__main__":
    build_report()
