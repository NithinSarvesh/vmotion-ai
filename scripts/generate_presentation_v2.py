"""
VMotion AI — Final Humanized DA1 Presentation Generator
Generates a polished, minimal, high-end 18-slide PowerPoint presentation (.pptx)
designed for a B.Tech CSE capstone/DA1 viva at VIT Chennai.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_PPTX = r"d:\projects\vmotion ai\VMotion_AI_DA1_Presentation_FINAL.pptx"
SCREENSHOTS_DIR = r"d:\projects\vmotion ai\VMotion_AI_DA1_Screenshots"

# Visual Theme Constants (Clean, Modern Light Theme)
BG_CANVAS = RGBColor(248, 250, 252)        # Slate 50 (#F8FAFC)
CARD_BG = RGBColor(255, 255, 255)          # Pure White (#FFFFFF)
CARD_BORDER = RGBColor(226, 232, 240)      # Slate 200 (#E2E8F0)
TEXT_DARK = RGBColor(15, 23, 42)           # Slate 900 (#0F172A)
TEXT_BODY = RGBColor(51, 65, 85)           # Slate 700 (#334155)
TEXT_MUTED = RGBColor(100, 116, 139)       # Slate 500 (#64748B)

ACCENT_BLUE = RGBColor(37, 99, 235)        # Blue 600 (#2563EB)
ACCENT_INDIGO = RGBColor(79, 70, 229)      # Indigo 600 (#4F46E5)
ACCENT_GREEN = RGBColor(16, 185, 129)      # Emerald 500 (#10B981)
ACCENT_AMBER = RGBColor(217, 119, 6)       # Amber 600 (#D97706)
ACCENT_RED = RGBColor(220, 38, 38)         # Red 600 (#DC2626)

PILL_BG = RGBColor(241, 245, 249)          # Slate 100 (#F1F5F9)

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_base_slide(tag, title, subtitle=""):
        slide = prs.slides.add_slide(blank_layout)

        # Background canvas
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_CANVAS
        bg.line.fill.background()

        # Header Container
        header = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.95))
        header.fill.solid()
        header.fill.fore_color.rgb = CARD_BG
        header.line.color.rgb = CARD_BORDER
        header.line.width = Pt(1)

        htf = header.text_frame
        htf.word_wrap = True
        htf.margin_left = Inches(0.3)
        htf.margin_top = Inches(0.12)
        htf.margin_right = Inches(0.3)
        htf.margin_bottom = Inches(0.1)

        p1 = htf.paragraphs[0]
        p1.text = tag.upper()
        p1.font.name = "Arial"
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_BLUE

        p2 = htf.add_paragraph()
        p2.text = title
        p2.font.name = "Arial"
        p2.font.size = Pt(17)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_DARK

        # Clean Minimal Footer
        fb = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
        ftf = fb.text_frame
        ftf.margin_left = ftf.margin_top = ftf.margin_right = ftf.margin_bottom = 0
        fp = ftf.paragraphs[0]
        fp.text = "VMotion AI | DA1 Evaluation | VIT Chennai"
        fp.font.name = "Arial"
        fp.font.size = Pt(9)
        fp.font.color.rgb = TEXT_MUTED

        return slide

    def add_card(slide, left, top, width, height, title="", border_color=CARD_BORDER, bg_color=CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)

        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.35))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title.upper()
            p.font.name = "Arial"
            p.font.size = Pt(10)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
        return card

    # =========================================================================
    # SLIDE 1: CLEAN MINIMAL HERO TITLE SLIDE
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid(); bg1.fill.fore_color.rgb = BG_CANVAS; bg1.line.fill.background()

    hero_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(0.8), Inches(10.933), Inches(5.9))
    hero_card.fill.solid(); hero_card.fill.fore_color.rgb = CARD_BG
    hero_card.line.color.rgb = CARD_BORDER; hero_card.line.width = Pt(1.5)

    htf = hero_card.text_frame
    htf.word_wrap = True
    htf.margin_left = Inches(0.8); htf.margin_right = Inches(0.8); htf.margin_top = Inches(0.8)

    p0 = htf.paragraphs[0]
    p0.text = "B.TECH CAPSTONE EVALUATION • DIGITAL ASSIGNMENT 1 (DA1)"
    p0.font.name = "Arial"; p0.font.size = Pt(10.5); p0.font.bold = True; p0.font.color.rgb = ACCENT_BLUE; p0.space_after = Pt(10)

    p1 = htf.add_paragraph()
    p1.text = "VMotion AI"
    p1.font.name = "Arial"; p1.font.size = Pt(40); p1.font.bold = True; p1.font.color.rgb = TEXT_DARK; p1.space_after = Pt(8)

    p2 = htf.add_paragraph()
    p2.text = "AI-Powered Virtual Machine Migration using Reinforcement Learning"
    p2.font.name = "Arial"; p2.font.size = Pt(16); p2.font.color.rgb = TEXT_BODY; p2.space_after = Pt(36)

    # Student Details Box
    student_box = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.0), Inches(3.8), Inches(9.333), Inches(2.2))
    student_box.fill.solid(); student_box.fill.fore_color.rgb = PILL_BG
    student_box.line.color.rgb = CARD_BORDER; student_box.line.width = Pt(1)

    stf = student_box.text_frame
    stf.word_wrap = True
    stf.margin_left = Inches(0.4); stf.margin_right = Inches(0.4); stf.margin_top = Inches(0.3)

    p = stf.paragraphs[0]
    p.text = "Nithin Sarvesh M"
    p.font.name = "Arial"; p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(4)

    p = stf.add_paragraph()
    p.text = "B.Tech Computer Science and Engineering"
    p.font.name = "Arial"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = TEXT_DARK; p.space_after = Pt(2)

    p = stf.add_paragraph()
    p.text = "School of Computer Science and Engineering (SCOPE)"
    p.font.name = "Arial"; p.font.size = Pt(11); p.font.color.rgb = TEXT_BODY; p.space_after = Pt(2)

    p = stf.add_paragraph()
    p.text = "Vellore Institute of Technology (VIT), Chennai, Tamil Nadu, India"
    p.font.name = "Arial"; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = TEXT_BODY

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT (Visual Problem -> Consequence Flow)
    # =========================================================================
    s2 = add_base_slide("Problem Overview", "Why Traditional VM Migration Needs an Intelligent Approach")

    # Left: Process Pipeline of the Problem
    chain_w = Inches(5.6)
    c_prob = add_card(s2, Inches(0.8), Inches(1.6), chain_w, Inches(5.2), "The Core Infrastructure Dilemma")
    ptf = c_prob.text_frame; ptf.margin_top = Inches(0.5); ptf.margin_left = Inches(0.3); ptf.word_wrap = True

    steps = [
        ("1. Dynamic Workload Bursts", "User traffic spikes unpredictably on cloud servers."),
        ("2. Resource Hotspots", "One server hits 90%+ CPU while neighboring servers stay underutilized."),
        ("3. SLA Degradation", "Customer applications experience latency spikes and slow responses."),
        ("4. Flapping & Thrashing", "Static rules (e.g. CPU > 80%) trigger migrations back and forth repeatedly."),
        ("5. Operator Bottleneck", "Manual intervention takes minutes; by then, performance has already dropped.")
    ]
    for i, (head, desc) in enumerate(steps):
        p = ptf.paragraphs[0] if i == 0 else ptf.add_paragraph()
        p.text = head
        p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE
        p2 = ptf.add_paragraph()
        p2.text = desc
        p2.font.name = "Arial"; p2.font.size = Pt(10); p2.font.color.rgb = TEXT_BODY; p2.space_after = Pt(6)

    # Right: Problem Statement Definition
    c_def = add_card(s2, Inches(6.733), Inches(1.6), Inches(5.8), Inches(5.2), "Problem Statement & Challenge", border_color=ACCENT_BLUE)
    dtf = c_def.text_frame; dtf.margin_top = Inches(0.5); dtf.margin_left = Inches(0.3); dtf.word_wrap = True

    p = dtf.paragraphs[0]
    p.text = "PROBLEM STATEMENT:"
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(6)

    p = dtf.add_paragraph()
    p.text = "\"How can we automatically rebalance virtual machines across infrastructure nodes using reinforcement learning, while ensuring that the AI cannot make unsafe or destabilizing migration decisions?\""
    p.font.name = "Arial"; p.font.size = Pt(13); p.font.italic = True; p.font.color.rgb = TEXT_DARK; p.space_after = Pt(16)

    p = dtf.add_paragraph()
    p.text = "Key Challenges We Address:"
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = TEXT_DARK; p.space_after = Pt(4)

    challenges = [
        "Multi-metric trade-offs: balancing CPU, RAM, network, and migration cost simultaneously.",
        "Preventing AI mistakes: pure RL models can hallucinate or suggest unsafe destinations.",
        "Migration cost awareness: each migration consumes network bandwidth and hypervisor CPU.",
        "Human oversight: giving system operators full visibility and final approval."
    ]
    for c in challenges:
        p = dtf.add_paragraph()
        p.text = f"• {c}"
        p.font.name = "Arial"; p.font.size = Pt(10); p.font.color.rgb = TEXT_BODY; p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 3: MOTIVATION (3-4 Visual Cards)
    # =========================================================================
    s3 = add_base_slide("Motivation", "Why Intelligent Migration Matters in Cloud Infrastructure")

    card_w3 = Inches(5.7)
    card_h3 = Inches(2.45)

    mots = [
        ("1. Dynamic Workload Demands", "Cloud applications fluctuate constantly throughout the day. Static threshold rules cannot look ahead or account for how workloads interact on the same physical host.", Inches(0.8), Inches(1.6), ACCENT_BLUE),
        ("2. Smarter Resource Balancing", "Live migration allows moving a running VM with negligible user downtime. Doing this intelligently balances cluster load, improves fairness, and avoids server throttling.", Inches(6.833), Inches(1.6), ACCENT_INDIGO),
        ("3. Accounting for Migration Costs", "Moving a VM is not free. It consumes interconnect bandwidth and hypervisor memory cycles. An intelligent agent learns to migrate only when the benefit outweighs the transient cost.", Inches(0.8), Inches(4.3), ACCENT_AMBER),
        ("4. Why a Safety Layer Is Needed", "A reinforcement learning model is a statistical decision-maker. We should never let an AI directly run infrastructure commands without a deterministic safety gate verifying capacity first.", Inches(6.833), Inches(4.3), ACCENT_GREEN)
    ]

    for title, desc, x, y, col in mots:
        c = add_card(s3, x, y, card_w3, card_h3, title, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.5); ctf.margin_left = Inches(0.25); ctf.word_wrap = True
        p = ctf.paragraphs[0]
        p.text = desc
        p.font.name = "Arial"; p.font.size = Pt(10.5); p.font.color.rgb = TEXT_BODY; p.line_spacing = 1.2

    # =========================================================================
    # SLIDE 4: OBJECTIVES (Clean Numbered Cards)
    # =========================================================================
    s4 = add_base_slide("Project Scope", "What VMotion AI Was Built to Achieve")

    # 4 Cards across
    col_w4 = Inches(5.7)
    col_h4 = Inches(2.45)

    objs = [
        ("1. Real-Time Telemetry & State Encoding", "Collect node and VM metrics (CPU, RAM, Network, Disk) and convert them into a normalized 103-dimensional state vector that the RL model can understand.", Inches(0.8), Inches(1.6), ACCENT_BLUE),
        ("2. Reinforcement Learning with PPO", "Train a MaskablePPO agent on a Discrete(7) action space with cooldown action masking to identify which virtual machine should be migrated.", Inches(6.833), Inches(1.6), ACCENT_INDIGO),
        ("3. Deterministic 8-Rule Safety Gate", "Build a separate software layer that independently checks target CPU, RAM headroom, node health, quorum, and cooldown before any migration can proceed.", Inches(0.8), Inches(4.3), ACCENT_GREEN),
        ("4. Operator Approval & Verification", "Require explicit human operator approval by default, track migrations across a 12-state FSM, and verify guest-agent health after migration.", Inches(6.833), Inches(4.3), ACCENT_AMBER)
    ]

    for title, desc, x, y, col in objs:
        c = add_card(s4, x, y, col_w4, col_h4, title, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.5); ctf.margin_left = Inches(0.25); ctf.word_wrap = True
        p = ctf.paragraphs[0]
        p.text = desc
        p.font.name = "Arial"; p.font.size = Pt(10.5); p.font.color.rgb = TEXT_BODY; p.line_spacing = 1.2

    # =========================================================================
    # SLIDE 5: EXISTING VS PROPOSED (Clean Minimal Table)
    # =========================================================================
    s5 = add_base_slide("Comparison", "Existing Migration Approaches vs. VMotion AI")

    table_s5 = s5.shapes.add_table(6, 3, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.1))
    t5 = table_s5.table
    t5.columns[0].width = Inches(2.3)
    t5.columns[1].width = Inches(4.7)
    t5.columns[2].width = Inches(4.733)

    h5 = ["Evaluation Aspect", "Traditional Threshold / Heuristic Approach", "VMotion AI Approach"]
    for idx, h in enumerate(h5):
        cell = t5.cell(0, idx)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_DARK
        p = cell.text_frame.paragraphs[0]
        p.text = h; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = RGBColor(255, 255, 255)

    comp_rows = [
        ("Decision Strategy", "Static rule triggers (e.g., if CPU > 80% then migrate). Reactive only.", "Reinforcement Learning (PPO) optimizes for overall cluster balance over time."),
        ("Cluster Awareness", "Looks at single-server metrics; misses cluster-wide load skew.", "103-feature state vector tracks all nodes, VMs, and cluster fairness."),
        ("Flapping Prevention", "Crude delays; VMs often migrate back and forth during load spikes.", "60-second cooldown dynamically enforced via invalid action masking."),
        ("Safety & Reliability", "Rules execute directly on servers; no independent verification step.", "Separate 8-rule safety gate verifies target capacity before any command runs."),
        ("Human Control", "Either completely manual (slow tickets) or unmonitored script execution.", "Two-phase workflow: operator sees AI recommendation and must approve it.")
    ]

    for r_idx, (dim, trad, prop) in enumerate(comp_rows, start=1):
        c0 = t5.cell(r_idx, 0); c0.fill.solid(); c0.fill.fore_color.rgb = PILL_BG
        p = c0.text_frame.paragraphs[0]; p.text = dim; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_DARK

        c1 = t5.cell(r_idx, 1); c1.fill.solid(); c1.fill.fore_color.rgb = CARD_BG
        p = c1.text_frame.paragraphs[0]; p.text = trad; p.font.name = "Arial"; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_BODY

        c2 = t5.cell(r_idx, 2); c2.fill.solid(); c2.fill.fore_color.rgb = CARD_BG
        p = c2.text_frame.paragraphs[0]; p.text = prop; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = ACCENT_BLUE

    # =========================================================================
    # SLIDE 6: SYSTEM ARCHITECTURE (Visual Multi-Tier Flow)
    # =========================================================================
    s6 = add_base_slide("System Design", "Decoupled Multi-Tier System Architecture")

    tier_w = Inches(11.733)
    tier_h = Inches(1.1)
    tier_y = Inches(1.6)
    gap_y = Inches(1.28)

    tiers = [
        ("TIER 1: INFRASTRUCTURE LAYER", 
         "Proxmox VE 9.x Cluster / High-Fidelity Simulation Engine",
         "Collects physical node telemetry, VM status, and handles live QEMU migration over cluster networking.", ACCENT_BLUE),

        ("TIER 2: TELEMETRY & 103-FEATURE OBSERVATION ADAPTER",
         "Feature Extractor, Rolling Telemetry Buffer, Jain's Fairness Calculator",
         "Converts raw cluster metrics into a normalized 103-dimensional state vector every 2 seconds.", ACCENT_INDIGO),

        ("TIER 3: REINFORCEMENT LEARNING DECISION ENGINE",
         "MaskablePPO Model (PPO V5) + Action Masking + Destination Resolver",
         "Evaluates cluster state, selects which VM to relocate, and resolves the best target node based on headroom.", ACCENT_AMBER),

        ("TIER 4: SAFETY GATE, OPERATOR APPROVAL & STATE MACHINE",
         "Deterministic 8-Rule Safety Gate, Stage 03 Operator Approval, 12-State Migration FSM",
         "Independently audits migration safety, requires operator signoff, streams task progress, and verifies guest health.", ACCENT_GREEN)
    ]

    for i, (t_head, t_main, t_desc, col) in enumerate(tiers):
        c = add_card(s6, Inches(0.8), tier_y + i*gap_y, tier_w, tier_h, border_color=col)
        ctf = c.text_frame; ctf.margin_top = Inches(0.12); ctf.margin_left = Inches(0.3); ctf.word_wrap = True
        
        p = ctf.paragraphs[0]; p.text = t_head; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = col
        p1 = ctf.add_paragraph(); p1.text = t_main; p1.font.name = "Arial"; p1.font.bold = True; p1.font.size = Pt(11); p1.font.color.rgb = TEXT_DARK
        p2 = ctf.add_paragraph(); p2.text = t_desc; p2.font.name = "Arial"; p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_BODY

    # =========================================================================
    # SLIDE 7: SYSTEM WORKFLOW (Step-by-Step Flowchart)
    # =========================================================================
    s7 = add_base_slide("Workflow", "End-to-End Migration Lifecycle (Step by Step)")

    card_w7 = Inches(2.75)
    card_h7 = Inches(2.4)
    gap_x7 = Inches(0.24)
    gap_y7 = Inches(0.24)
    x7_start = Inches(0.8)

    w_steps = [
        ("Step 1: Collect Telemetry", "Query hypervisor or simulation every 2 seconds for CPU, RAM, Disk, and Network stats.", ACCENT_BLUE),
        ("Step 2: Build 103-Dim State", "Normalize raw telemetry into a unified feature vector bounded between -1.0 and 1.0.", ACCENT_BLUE),
        ("Step 3: Mask Invalid Actions", "Disable any VM currently in a 60s cooldown or in a stopped state from being selected.", ACCENT_INDIGO),
        ("Step 4: PPO Policy Evaluation", "The PPO V5 model evaluates the state vector and recommends the best VM to migrate.", ACCENT_INDIGO),
        ("Step 5: Pick Best Target Host", "Headroom resolver identifies the host with the most available CPU/RAM capacity.", ACCENT_AMBER),
        ("Step 6: Run Safety Gate Checks", "8 deterministic rules check memory margin, CPU ceiling, node health, and quorum.", ACCENT_AMBER),
        ("Step 7: Operator Approval", "Proposal appears on dashboard; human administrator approves or rejects the action.", ACCENT_GREEN),
        ("Step 8: Execute & Verify Health", "Dispatch migration, monitor task progress, verify destination placement, and ping guest agent.", ACCENT_GREEN)
    ]

    for i, (head, desc, col) in enumerate(w_steps):
        row = i // 4
        col_idx = i % 4
        x = x7_start + col_idx * (card_w7 + gap_x7)
        y = Inches(1.6) + row * (card_h7 + gap_y7)

        c = add_card(s7, x, y, card_w7, card_h7, border_color=col)
        ctf = c.text_frame; ctf.margin_top = Inches(0.18); ctf.margin_left = Inches(0.2); ctf.margin_right = Inches(0.2); ctf.word_wrap = True
        p = ctf.paragraphs[0]; p.text = head; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = col; p.space_after = Pt(6)
        p1 = ctf.add_paragraph(); p1.text = desc; p1.font.name = "Arial"; p1.font.size = Pt(10); p1.font.color.rgb = TEXT_BODY; p1.line_spacing = 1.2

    # =========================================================================
    # SLIDE 8: MODULE BREAKDOWN (Clean Modular Cards)
    # =========================================================================
    s8 = add_base_slide("Implementation Modules", "Core Software Components in the VMotion AI Repository")

    # 6 cards (2 rows of 3)
    card_w8 = Inches(3.75)
    card_h8 = Inches(2.45)
    gap_x8 = Inches(0.24)
    gap_y8 = Inches(0.25)

    mods = [
        ("Telemetry & Adapter", "Polls hypervisors and extracts the 103-dimensional state vector with bounds checking [-1, 1].", "COMPLETE", ACCENT_BLUE),
        ("PPO Decision Engine", "Loads trained MaskablePPO weights, evaluates policy distributions, and provides heuristic fallback.", "COMPLETE (V5)", ACCENT_INDIGO),
        ("Deterministic Safety Gate", "Independently enforces 8 physical capacity rules; operates fail-closed to block unsafe actions.", "COMPLETE", ACCENT_GREEN),
        ("Migration FSM Planner", "Tracks each migration across 12 states, manages operator approval, and verifies post-placement state.", "COMPLETE", ACCENT_AMBER),
        ("Proxmox VE Provider", "Connects to Proxmox REST API v2, parses task UPIDs, and checks QEMU guest-agent health.", "MOCK TESTED", ACCENT_BLUE),
        ("Control Dashboard (UI)", "React 19 and Three.js 3D web interface showing real-time cluster state, AI reasoning, and audit logs.", "COMPLETE", ACCENT_GREEN)
    ]

    for i, (m_name, m_desc, m_stat, col) in enumerate(mods):
        row = i // 3
        col_idx = i % 3
        x = Inches(0.8) + col_idx * (card_w8 + gap_x8)
        y = Inches(1.6) + row * (card_h8 + gap_y8)

        c = add_card(s8, x, y, card_w8, card_h8, m_name, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.5); ctf.margin_left = Inches(0.25); ctf.word_wrap = True

        p = ctf.paragraphs[0]; p.text = m_desc; p.font.name = "Arial"; p.font.size = Pt(10); p.font.color.rgb = TEXT_BODY; p.space_after = Pt(12)
        p1 = ctf.add_paragraph(); p1.text = f"Status: {m_stat}"; p1.font.name = "Arial"; p1.font.bold = True; p1.font.size = Pt(9.5); p1.font.color.rgb = col

    # =========================================================================
    # SLIDE 9: REINFORCEMENT LEARNING SETUP (Visual Diagram)
    # =========================================================================
    s9 = add_base_slide("Reinforcement Learning", "How the PPO Model Makes Migration Decisions")

    card_w9 = Inches(5.7)
    card_h9 = Inches(5.2)

    # Left: State & Action
    cl = add_card(s9, Inches(0.8), Inches(1.6), card_w9, card_h9, "State & Action Formulation")
    ltf = cl.text_frame; ltf.margin_top = Inches(0.5); ltf.margin_left = Inches(0.3); ltf.word_wrap = True

    p = ltf.paragraphs[0]; p.text = "103-FEATURE OBSERVATION VECTOR:"
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(4)

    p1 = ltf.add_paragraph()
    p1.text = "• 24 Node Features (0..23): CPU util, RAM util, network RX/TX, disk util, and headroom for all 3 nodes.\n• 60 VM Features (24..83): CPU util, RAM allocated, RAM used, network IO, SLA priority, cooldown timer, uptime, and host ID for 6 VMs.\n• 19 Cluster Features (84..102): Jain's Fairness Index (CPU/RAM), standard deviation, power index, quorum, and storage health."
    p1.font.name = "Arial"; p1.font.size = Pt(10); p1.font.color.rgb = TEXT_BODY; p1.space_after = Pt(16)

    p2 = ltf.add_paragraph(); p2.text = "DISCRETE(7) ACTION SPACE:"
    p2.font.name = "Arial"; p2.font.bold = True; p2.font.size = Pt(11); p2.font.color.rgb = ACCENT_BLUE; p2.space_after = Pt(4)

    p3 = ltf.add_paragraph()
    p3.text = "• Action 0 = No-Op (Leave cluster as is; cluster in equilibrium).\n• Actions 1..6 = Migrate VM 1 through 6.\n• Destination Target = Chosen deterministically by finding the node with the highest unallocated capacity.\n• Action Masking = Masks out VMs that migrated within the last 60 seconds or are currently stopped."
    p3.font.name = "Arial"; p3.font.size = Pt(10); p3.font.color.rgb = TEXT_BODY

    # Right: Reward Function
    cr = add_card(s9, Inches(6.833), Inches(1.6), card_w9, card_h9, "Multi-Objective Reward Function", border_color=ACCENT_INDIGO)
    rtf = cr.text_frame; rtf.margin_top = Inches(0.5); rtf.margin_left = Inches(0.3); rtf.word_wrap = True

    p = rtf.paragraphs[0]; p.text = "BALANCING GOALS & PENALTIES:"
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_INDIGO; p.space_after = Pt(4)

    p1 = rtf.add_paragraph()
    p1.text = "Reward = Balance + Stability - SLA Penalty - Overload Penalty - Migration Cost"
    p1.font.name = "Arial"; p1.font.bold = True; p1.font.size = Pt(10.5); p1.font.color.rgb = TEXT_DARK; p1.space_after = Pt(12)

    rew_items = [
        ("+ Load Balance Dividend", "Rewards uniform CPU spread across servers using Jain's Fairness Index (+2.5 * Jain)."),
        ("+ Stability Bonus", "+1.0 reward for choosing No-Op when cluster is already well balanced (prevents flapping)."),
        ("- SLA Breach Penalty", "-2.0 penalty whenever a workload exceeds its assigned SLA ceiling."),
        ("- Host Overload Penalty", "-4.0 penalty if any server exceeds 85% CPU capacity (heavy penalty)."),
        ("- Migration Overhead", "-0.8 cost for each migration to account for network bandwidth and memory copying.")
    ]
    for head, desc in rew_items:
        p = rtf.add_paragraph(); p.text = head; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_DARK
        p1 = rtf.add_paragraph(); p1.text = desc; p1.font.name = "Arial"; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_BODY; p1.space_after = Pt(4)

    # =========================================================================
    # SLIDE 10: EXPERIMENTAL RESULTS (Visual Cards with Delta Points)
    # =========================================================================
    s10 = add_base_slide("Experimental Results", "Comparing PPO V4 (Collapse) with PPO V5 (Balanced Training)")

    # 4 Large Metric Visual Cards
    m_w10 = Inches(2.75)
    m_h10 = Inches(2.6)
    gap10 = Inches(0.24)
    y10_top = Inches(1.6)

    m_cards = [
        ("Overall Mean Reward", "V4: -263.48", "V5: +55.81", "+319.29 points", "V5 actively balances cluster", ACCENT_GREEN),
        ("Unseen Test Split", "V4: -53.16", "V5: +154.93", "+208.09 points", "Strong generalization", ACCENT_GREEN),
        ("Server Overload Steps", "V4: 60.22", "V5: 7.33", "-52.89 steps", "-87.8% hotspot time", ACCENT_BLUE),
        ("Jain's Fairness Index", "V4: 0.7682", "V5: 0.9288", "+0.1606", "Significant balance gain", ACCENT_INDIGO)
    ]

    for i, (title, v4, v5, delta, note, col) in enumerate(m_cards):
        x = Inches(0.8) + i * (m_w10 + gap10)
        c = add_card(s10, x, y10_top, m_w10, m_h10, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.2); ctf.margin_left = Inches(0.2); ctf.word_wrap = True

        p = ctf.paragraphs[0]; p.text = title; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = TEXT_DARK; p.space_after = Pt(8)
        p1 = ctf.add_paragraph(); p1.text = v4; p1.font.name = "Arial"; p1.font.size = Pt(10); p1.font.color.rgb = TEXT_MUTED
        p2 = ctf.add_paragraph(); p2.text = v5; p2.font.name = "Arial"; p2.font.bold = True; p2.font.size = Pt(14); p2.font.color.rgb = col; p2.space_after = Pt(4)
        p3 = ctf.add_paragraph(); p3.text = f"Change: {delta}"; p3.font.name = "Arial"; p3.font.bold = True; p3.font.size = Pt(10); p3.font.color.rgb = col
        p4 = ctf.add_paragraph(); p4.text = note; p4.font.name = "Arial"; p4.font.size = Pt(9); p4.font.color.rgb = TEXT_BODY

    # Diagnostic Insight Card below
    diag_c = add_card(s10, Inches(0.8), Inches(4.5), Inches(11.733), Inches(2.3), "Key Takeaway: Fixing Training Distribution Collapse")
    dtf = diag_c.text_frame; dtf.margin_top = Inches(0.45); dtf.margin_left = Inches(0.3); dtf.word_wrap = True

    p = dtf.paragraphs[0]
    p.text = "• Why V4 Failed: PPO V4 was trained on 100% normal, balanced data. Since normal states penalize migrations, the model learned that doing nothing (No-Op) was always best. When tested on severe hotspots, it refused to migrate (0.0 migrations)."
    p.font.name = "Arial"; p.font.size = Pt(10); p.font.color.rgb = TEXT_BODY; p.space_after = Pt(6)

    p1 = dtf.add_paragraph()
    p1.text = "• How V5 Succeeded: We introduced a balanced 4-scenario sampler (25% Normal, 25% CPU Hotspot, 25% RAM Hotspot, 25% Mixed Overload). By seeing hotspots during training, PPO V5 learned to take targeted action (averaging 2.07 migrations per episode), outperforming baseline heuristics on unseen test scenarios (+154.93)."
    p1.font.name = "Arial"; p1.font.bold = True; p1.font.size = Pt(10); p1.font.color.rgb = ACCENT_BLUE

    # =========================================================================
    # SLIDE 11: SAFETY GATE (8 Compact Rule Cards)
    # =========================================================================
    s11 = add_base_slide("Safety Layer", "Deterministic Safety Gate: 8 Checks Before Migration")

    col_w11 = Inches(5.7)
    col_h11 = Inches(1.15)
    gap_y11 = Inches(0.15)

    rules = [
        ("1. VM Running State", "Confirms the VM exists and is currently in a running hypervisor state."),
        ("2. Distinct Target Host", "Ensures source and destination are two different physical servers (src != dest)."),
        ("3. Source Node Health", "Checks that the source hypervisor daemon has active heartbeat and no alarms."),
        ("4. Target Node Health", "Ensures the destination server is online and reachable over the cluster network."),
        ("5. Target RAM Headroom", "Target unallocated RAM must fit the VM plus a 20% safety buffer."),
        ("6. Target CPU Capacity", "Projected CPU utilization on the target after migration must remain below 85%."),
        ("7. Storage & Quorum", "Verifies target datastore accessibility and cluster quorum consensus."),
        ("8. 60-Second Cooldown", "Prevents migrating a VM that was relocated less than 60 seconds ago.")
    ]

    for idx, (r_name, r_desc) in enumerate(rules):
        col_idx = idx // 4
        row_idx = idx % 4
        x = Inches(0.8) + col_idx * (col_w11 + Inches(0.33))
        y = Inches(1.6) + row_idx * (col_h11 + gap_y11)

        c = add_card(s11, x, y, col_w11, col_h11, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.15); ctf.margin_left = Inches(0.2); ctf.word_wrap = True
        p = ctf.paragraphs[0]; p.text = r_name; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10.5); p.font.color.rgb = ACCENT_BLUE
        p1 = ctf.add_paragraph(); p1.text = r_desc; p1.font.name = "Arial"; p1.font.size = Pt(9.5); p1.font.color.rgb = TEXT_BODY

    # Bottom summary callout
    f_box = s11.shapes.add_textbox(Inches(0.8), Inches(6.4), Inches(11.733), Inches(0.5))
    ftf = f_box.text_frame; ftf.margin_left = 0
    p = ftf.paragraphs[0]
    p.text = "CORE PRINCIPLE: The safety gate operates under fail-closed logic. If any check fails, the migration is blocked immediately, regardless of what the AI model recommended."
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = ACCENT_AMBER

    # =========================================================================
    # SLIDE 12: PROXMOX VE INTEGRATION
    # =========================================================================
    s12 = add_base_slide("Hypervisor Integration", "Proxmox VE 9.x Provider Architecture & Verification Status")

    card_w12 = Inches(5.7)
    card_h12 = Inches(5.2)

    # Left: API Architecture
    c_px = add_card(s12, Inches(0.8), Inches(1.6), card_w12, card_h12, "Proxmox VE REST Integration")
    pxtf = c_px.text_frame; pxtf.margin_top = Inches(0.5); pxtf.margin_left = Inches(0.3); pxtf.word_wrap = True

    px_steps = [
        ("REST API v2 (Port 8006)", "Communicates with Proxmox VE 9.x over HTTPS using privilege-separated API tokens (vmotion-api@pve!automation -privsep 1)."),
        ("Least Privilege Roles", "Audited minimum permissions: Sys.Audit, VM.Audit, VM.Migrate, VM.Allocate, Datastore.Audit, Datastore.AllocateSpace, VM.GuestAgent.Audit."),
        ("Asynchronous Task UPID", "Migration returns a UPID (Unique Process ID); VMotion AI polls the task every 1 second until complete."),
        ("Guest Agent Health Check", "After migration, queries the QEMU guest agent (GET .../agent/ping) to confirm the guest OS is responsive.")
    ]
    for head, desc in px_steps:
        p = pxtf.add_paragraph(); p.text = head; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10.5); p.font.color.rgb = ACCENT_BLUE
        p1 = pxtf.add_paragraph(); p1.text = desc; p1.font.name = "Arial"; p1.font.size = Pt(9.5); p1.font.color.rgb = TEXT_BODY; p1.space_after = Pt(8)

    # Right: Honest Status Breakdown
    c_stat = add_card(s12, Inches(6.833), Inches(1.6), card_w12, card_h12, "Current Implementation & Verification Status", border_color=ACCENT_AMBER)
    stf = c_stat.text_frame; stf.margin_top = Inches(0.5); stf.margin_left = Inches(0.3); stf.word_wrap = True

    statuses = [
        ("Proxmox API Client Code", "COMPLETE", "Fully written in backend/app/providers/proxmox.py"),
        ("Token Auth & Header Logic", "COMPLETE", "Privilege separation & secret masking implemented"),
        ("UPID Task Parsing & Polling", "COMPLETE", "Tested against simulated Proxmox responses"),
        ("Guest Agent Ping Endpoint", "COMPLETE", "Real API operation implemented in provider"),
        ("Unit & Mock Test Suite", "COMPLETE", "Passes automated mock integration tests"),
        ("Physical Server Migration", "PENDING", "Awaiting validation on physical lab hardware"),
    ]
    for head, stat, note in statuses:
        p = stf.add_paragraph()
        p.text = f"• {head}: "
        p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_DARK
        r = p.add_run()
        r.text = f"[{stat}]"
        r.font.bold = True
        r.font.color.rgb = ACCENT_GREEN if stat == "COMPLETE" else (ACCENT_AMBER if stat == "PENDING" else TEXT_MUTED)
        p1 = stf.add_paragraph()
        p1.text = f"  {note}"
        p1.font.name = "Arial"; p1.font.size = Pt(8.5); p1.font.color.rgb = TEXT_MUTED; p1.space_after = Pt(2)

    # =========================================================================
    # SLIDE 13: USER INTERFACE (3 Key High-Resolution Screenshots)
    # =========================================================================
    s13 = add_base_slide("Control Plane UI", "Real-Time 3D Cluster Monitoring & Decision Dashboard")

    img1 = os.path.join(SCREENSHOTS_DIR, "01_hero_spatial_overview.png")
    img2 = os.path.join(SCREENSHOTS_DIR, "02_ai_engine_decision_pipeline.png")

    if os.path.exists(img1):
        s13.shapes.add_picture(img1, Inches(0.8), Inches(1.6), width=Inches(5.7))
    else:
        add_card(s13, Inches(0.8), Inches(1.6), Inches(5.7), Inches(3.6), "[SCREENSHOT: 3D CLUSTER]")

    if os.path.exists(img2):
        s13.shapes.add_picture(img2, Inches(6.833), Inches(1.6), width=Inches(5.7))
    else:
        add_card(s13, Inches(6.833), Inches(1.6), Inches(5.7), Inches(3.6), "[SCREENSHOT: AI ENGINE]")

    # Simple Captions Below
    c1 = add_card(s13, Inches(0.8), Inches(5.0), Inches(5.7), Inches(1.8), "3D Cluster Overview & Telemetry")
    c1tf = c1.text_frame; c1tf.margin_top = Inches(0.4); c1tf.margin_left = Inches(0.2); c1tf.word_wrap = True
    p = c1tf.paragraphs[0]
    p.text = "Displays interactive Three.js 3D cluster with host pedestals proportional to CPU load, orbiting VMs with SLA priority rings, and cluster-wide telemetry figures."
    p.font.name = "Arial"; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_BODY

    c2 = add_card(s13, Inches(6.833), Inches(5.0), Inches(5.7), Inches(1.8), "AI Decision Pipeline & Schema Explorer")
    c2tf = c2.text_frame; c2tf.margin_top = Inches(0.4); c2tf.margin_left = Inches(0.2); c2tf.word_wrap = True
    p = c2tf.paragraphs[0]
    p.text = "Shows current PPO policy recommendation, selection probability, frozen model artifact status (PPO V5), and 103-dimensional state vector breakdown."
    p.font.name = "Arial"; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_BODY

    # =========================================================================
    # SLIDE 14: PROJECT PROGRESS & COMPLETION DASHBOARD
    # =========================================================================
    s14 = add_base_slide("Project Completion", "Implementation Progress & Defensible Completion Breakdown")

    # Left: Progress Dashboard (Two Big Numbers)
    c_p1 = add_card(s14, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.2), "Verified Completion Status")
    ptf1 = c_p1.text_frame; ptf1.margin_top = Inches(0.5); ptf1.margin_left = Inches(0.3); ptf1.word_wrap = True

    p = ptf1.paragraphs[0]; p.text = "SOFTWARE IMPLEMENTATION:"; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10.5); p.font.color.rgb = ACCENT_BLUE
    p1 = ptf1.add_paragraph(); p1.text = "91.5%"; p1.font.name = "Arial"; p1.font.bold = True; p1.font.size = Pt(36); p1.font.color.rgb = ACCENT_GREEN; p1.space_after = Pt(6)
    p2 = ptf1.add_paragraph()
    p2.text = "All software components—FastAPI backend, 103-feature adapter, PPO V5 model, deterministic safety gate, 12-state FSM, 3D frontend, and 96 automated tests—are fully written and verified."
    p2.font.name = "Arial"; p2.font.size = Pt(10); p2.font.color.rgb = TEXT_BODY; p2.space_after = Pt(18)

    p3 = ptf1.add_paragraph(); p3.text = "PHYSICAL HARDWARE VALIDATION:"; p3.font.name = "Arial"; p3.font.bold = True; p3.font.size = Pt(10.5); p3.font.color.rgb = ACCENT_AMBER
    p4 = ptf1.add_paragraph(); p4.text = "Pending Lab Test"; p4.font.name = "Arial"; p4.font.bold = True; p4.font.size = Pt(24); p4.font.color.rgb = ACCENT_AMBER; p4.space_after = Pt(6)
    p5 = ptf1.add_paragraph()
    p5.text = "Proxmox REST API code and token authentication are implemented and mock-tested, but real physical live migration over external servers remains pending laboratory rack scheduling."
    p5.font.name = "Arial"; p5.font.size = Pt(10); p5.font.color.rgb = TEXT_BODY

    # Right: Component Breakdown Table
    table_s14 = s14.shapes.add_table(10, 3, Inches(6.833), Inches(1.6), Inches(5.7), Inches(5.2))
    t14 = table_s14.table
    t14.columns[0].width = Inches(2.7)
    t14.columns[1].width = Inches(1.2)
    t14.columns[2].width = Inches(1.8)

    h14 = ["Component", "Weight", "Status"]
    for idx, h in enumerate(h14):
        cell = t14.cell(0, idx); cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_DARK
        p = cell.text_frame.paragraphs[0]; p.text = h; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = RGBColor(255, 255, 255)

    comp_items = [
        ("Architecture & Interface Specs", "10%", "100% Complete"),
        ("Backend & Control Plane", "15%", "100% Complete"),
        ("Telemetry & 103-Dim Adapter", "10%", "100% Complete"),
        ("PPO / Reinforcement Learning", "15%", "100% Complete (V5)"),
        ("Safety Gate & 12-State FSM", "15%", "100% Complete"),
        ("Hypervisor Provider Code", "10%", "75% (Mock Tested)"),
        ("Frontend Control Dashboard", "10%", "100% Complete"),
        ("Automated Tests & Benchmarks", "10%", "90% (96 Tests Pass)"),
        ("Documentation & Specifications", "5%", "100% Complete")
    ]
    for r_idx, (comp, wt, stat) in enumerate(comp_items, start=1):
        c0 = t14.cell(r_idx, 0); c0.fill.solid(); c0.fill.fore_color.rgb = PILL_BG
        p = c0.text_frame.paragraphs[0]; p.text = comp; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(8.5); p.font.color.rgb = TEXT_DARK

        c1 = t14.cell(r_idx, 1); c1.fill.solid(); c1.fill.fore_color.rgb = CARD_BG
        p = c1.text_frame.paragraphs[0]; p.text = wt; p.font.name = "Arial"; p.font.size = Pt(8.5); p.font.color.rgb = TEXT_MUTED

        c2 = t14.cell(r_idx, 2); c2.fill.solid(); c2.fill.fore_color.rgb = CARD_BG
        p = c2.text_frame.paragraphs[0]; p.text = stat; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(8.5)
        p.font.color.rgb = ACCENT_GREEN if "100%" in stat else ACCENT_AMBER

    # =========================================================================
    # SLIDE 15: TESTING & VALIDATION
    # =========================================================================
    s15 = add_base_slide("Testing & Validation", "Automated Regression Test Suite & Build Results")

    # 3 Large Metrics Top
    c_w15 = Inches(3.75)
    c_h15 = Inches(1.3)

    t1 = add_card(s15, Inches(0.8), Inches(1.6), c_w15, c_h15, "BACKEND TESTS (PYTEST)")
    ttf1 = t1.text_frame; ttf1.margin_top = Inches(0.45); ttf1.margin_left = Inches(0.2); ttf1.word_wrap = True
    p = ttf1.paragraphs[0]; p.text = "96 Passed / 0 Failed"; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(17); p.font.color.rgb = ACCENT_GREEN
    p1 = ttf1.add_paragraph(); p1.text = "Runtime: 19.47s across 11 test modules"; p1.font.name = "Arial"; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_MUTED

    t2 = add_card(s15, Inches(4.79), Inches(1.6), c_w15, c_h15, "FRONTEND BUILD (VITE)")
    ttf2 = t2.text_frame; ttf2.margin_top = Inches(0.45); ttf2.margin_left = Inches(0.2); ttf2.word_wrap = True
    p = ttf2.paragraphs[0]; p.text = "1,891 Modules Transformed"; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(17); p.font.color.rgb = ACCENT_BLUE
    p1 = ttf2.add_paragraph(); p1.text = "0 TypeScript errors • Clean bundle"; p1.font.name = "Arial"; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_MUTED

    t3 = add_card(s15, Inches(8.78), Inches(1.6), c_w15, c_h15, "BENCHMARK HARNESS")
    ttf3 = t3.text_frame; ttf3.margin_top = Inches(0.45); ttf3.margin_left = Inches(0.2); ttf3.word_wrap = True
    p = ttf3.paragraphs[0]; p.text = "600 Benchmark Episodes"; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(17); p.font.color.rgb = ACCENT_INDIGO
    p1 = ttf3.add_paragraph(); p1.text = "Evaluated across 10 distinct cluster scenarios"; p1.font.name = "Arial"; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_MUTED

    # Test Scope Breakdown Card Below
    t_det = add_card(s15, Inches(0.8), Inches(3.05), Inches(11.733), Inches(3.75), "Automated Test Coverage by Subsystem")
    dtf15 = t_det.text_frame; dtf15.margin_top = Inches(0.5); dtf15.margin_left = Inches(0.3); dtf15.word_wrap = True

    tests = [
        ("Safety Gate Tests (12 tests)", "Verifies all 8 rules block on: identical hosts, offline servers, stopped VMs, high RAM, high CPU, and active cooldown."),
        ("Migration Lifecycle Tests (10 tests)", "Asserts valid FSM progression (RECOMMENDED -> VERIFIED) and verifies illegal transitions raise InvalidStateTransitionError."),
        ("Observation Spec Tests (8 tests)", "Verifies exact 103 feature dimension, [-1.0, 1.0] mathematical bounds, and deterministic node/VM sorting order."),
        ("Provider Contract Tests (10 tests)", "Tests Simulation, Proxmox, and Libvirt providers for schema conformity, error handling, and truthful disconnection."),
        ("API & Security Tests (14 tests)", "Verifies FastAPI endpoints, token secret masking in /api/cluster/config, and live mode confirmation headers.")
    ]
    for head, desc in tests:
        p = dtf15.add_paragraph(); p.text = f"• {head}: "; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = TEXT_DARK
        r = p.add_run(); r.text = desc; r.font.name = "Arial"; r.font.size = Pt(9.5); r.font.color.rgb = TEXT_BODY; p.space_after = Pt(5)

    # =========================================================================
    # SLIDE 16: ACHIEVEMENTS
    # =========================================================================
    s16 = add_base_slide("Project Achievements", "What Has Been Accomplished in VMotion AI")

    card_w16 = Inches(5.7)
    card_h16 = Inches(2.45)

    achs = [
        ("1. Decoupled AI & Safety Architecture", "Proved that reinforcement learning can be safely used for cluster rebalancing by placing a deterministic, fail-closed safety gate between the AI and hypervisors.", Inches(0.8), Inches(1.6), ACCENT_BLUE),
        ("2. Overcoming Policy Collapse (PPO V5)", "Diagnosed why single-scenario training caused the model to collapse to zero migrations, and resolved it with balanced multi-scenario sampling (+319.29 reward gain).", Inches(6.833), Inches(1.6), ACCENT_GREEN),
        ("3. Complete 12-State FSM Lifecycle", "Built a stateful migration workflow that tracks Proxmox task UPIDs and verifies destination residency and QEMU guest health before marking a task complete.", Inches(0.8), Inches(4.3), ACCENT_INDIGO),
        ("4. Modern 3D Web Dashboard", "Developed an interactive React 19 control plane with Three.js 3D cluster visualization, real-time WebSocket telemetry, and append-only audit logging.", Inches(6.833), Inches(4.3), ACCENT_AMBER)
    ]

    for title, desc, x, y, col in achs:
        c = add_card(s16, x, y, card_w16, card_h16, title, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.5); ctf.margin_left = Inches(0.25); ctf.word_wrap = True
        p = ctf.paragraphs[0]; p.text = desc; p.font.name = "Arial"; p.font.size = Pt(10); p.font.color.rgb = TEXT_BODY; p.line_spacing = 1.2

    # =========================================================================
    # SLIDE 17: HONEST LIMITATIONS (Simulation Validated vs. Pending)
    # =========================================================================
    s17 = add_base_slide("Current Scope & Boundaries", "What Is Validated in Simulation vs. Pending Real Hardware")

    card_w17 = Inches(5.7)
    card_h17 = Inches(5.2)

    # Left: Validated
    c_val = add_card(s17, Inches(0.8), Inches(1.6), card_w17, card_h17, "Validated in Software & Simulation", border_color=ACCENT_GREEN)
    vtf = c_val.text_frame; vtf.margin_top = Inches(0.5); vtf.margin_left = Inches(0.3); vtf.word_wrap = True

    val_points = [
        ("103-Feature Telemetry Adapter", "Continuous normalized vector extraction validated against mathematical bounds."),
        ("PPO V5 Decision Model", "Trained model evaluated across 600 benchmark episodes with verified SHA-256 hash."),
        ("8-Rule Deterministic Safety Gate", "Independently verified to block invalid CPU, RAM, quorum, and cooldown states."),
        ("12-State Migration FSM", "State machine progression and illegal transition errors verified across 96 tests."),
        ("React 19 & Three.js Web UI", "Production frontend build passes with zero TypeScript or linting errors.")
    ]
    for head, desc in val_points:
        p = vtf.add_paragraph(); p.text = f"✔ {head}: "; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_GREEN
        r = p.add_run(); r.text = desc; r.font.name = "Arial"; r.font.size = Pt(9); r.font.color.rgb = TEXT_BODY; p.space_after = Pt(6)

    # Right: Pending
    c_pen = add_card(s17, Inches(6.833), Inches(1.6), card_w17, card_h17, "Pending Physical Hardware Validation", border_color=ACCENT_AMBER)
    ptf17 = c_pen.text_frame; ptf17.margin_top = Inches(0.5); ptf17.margin_left = Inches(0.3); ptf17.word_wrap = True

    pen_points = [
        ("Physical Proxmox Lab Rack", "Connecting to real physical servers in the college laboratory is pending hardware scheduling."),
        ("Live VM Memory Benchmarking", "Measuring dirty-page rate vs. actual 10 GbE network transfer speed on real hardware."),
        ("Two-Node Quorum in Lab", "A 2-node cluster requires deploying an external QDevice (corosync-qnetd) to avoid quorum loss."),
        ("Fixed Discrete Action Space", "Currently dimensioned for 3 nodes and 6 VMs; larger clusters will require Graph Neural Networks."),
        ("Windows Libvirt Dependency", "Native Libvirt C-bindings are missing on Windows; designated for future Linux agent deployment.")
    ]
    for head, desc in pen_points:
        p = ptf17.add_paragraph(); p.text = f"⏳ {head}: "; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_AMBER
        r = p.add_run(); r.text = desc; r.font.name = "Arial"; r.font.size = Pt(9); r.font.color.rgb = TEXT_BODY; p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 18: CONCLUSION & NEXT STEPS
    # =========================================================================
    s18 = add_base_slide("Conclusion", "Summary of Work Done & Next Steps")

    card_w18 = Inches(5.7)
    card_h18 = Inches(5.2)

    # Left: Summary
    c_sum = add_card(s18, Inches(0.8), Inches(1.6), card_w18, card_h18, "Project Summary")
    stf18 = c_sum.text_frame; stf18.margin_top = Inches(0.5); stf18.margin_left = Inches(0.3); stf18.word_wrap = True

    p = stf18.paragraphs[0]
    p.text = "WHAT VMOTION AI DOES:"
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(6)

    p1 = stf18.add_paragraph()
    p1.text = "\"VMotion AI combines reinforcement learning (PPO), a deterministic safety gate, and hypervisor APIs to make intelligent VM migration decisions without risking infrastructure stability.\""
    p1.font.name = "Arial"; p1.font.size = Pt(12); p1.font.italic = True; p1.font.color.rgb = TEXT_DARK; p1.space_after = Pt(16)

    p2 = stf18.add_paragraph()
    p2.text = "Key Verified Results:"
    p2.font.name = "Arial"; p2.font.bold = True; p2.font.size = Pt(10.5); p2.font.color.rgb = TEXT_DARK; p2.space_after = Pt(4)

    res_pts = [
        "PPO V5 model achieved +154.93 on unseen test scenarios.",
        "Server overload time reduced by 87.8% compared to V4.",
        "8 deterministic safety rules prevent illegal migrations.",
        "96 automated backend tests passing with zero failures.",
        "91.5% software implementation completion."
    ]
    for r in res_pts:
        p = stf18.add_paragraph()
        p.text = f"• {r}"
        p.font.name = "Arial"; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_BODY; p.space_after = Pt(3)

    # Right: Next Steps & Thank You
    c_nxt = add_card(s18, Inches(6.833), Inches(1.6), card_w18, card_h18, "Next Milestones", border_color=ACCENT_INDIGO)
    ntf18 = c_nxt.text_frame; ntf18.margin_top = Inches(0.5); ntf18.margin_left = Inches(0.3); ntf18.word_wrap = True

    p = ntf18.paragraphs[0]; p.text = "NEXT DEVELOPMENT STEPS:"; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_INDIGO; p.space_after = Pt(6)

    nxt_pts = [
        ("1. Lab Server Deployment", "Connect to physical Proxmox VE 9.2 server nodes in the VIT Chennai networking lab."),
        ("2. Deploy Corosync QDevice", "Add an external Raspberry Pi or VM running corosync-qnetd for quorum resilience in 2-node setups."),
        ("3. GNN Policy Exploration", "Investigate Graph Neural Networks to support clusters of arbitrary size (10+ nodes)."),
        ("4. Time-Series Predictive Pre-empting", "Use lightweight forecasting (e.g. ARIMA) to trigger migrations 2 minutes before contention peaks.")
    ]
    for head, desc in nxt_pts:
        p = ntf18.add_paragraph(); p.text = head; p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = TEXT_DARK
        p1 = ntf18.add_paragraph(); p1.text = desc; p1.font.name = "Arial"; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_BODY; p1.space_after = Pt(4)

    p_ty = ntf18.add_paragraph()
    p_ty.text = "\nThank You! Questions & Discussion Welcome."
    p_ty.font.name = "Arial"; p_ty.font.bold = True; p_ty.font.size = Pt(12); p_ty.font.color.rgb = ACCENT_BLUE

    # Save Presentation
    prs.save(OUTPUT_PPTX)
    print(f"Final Presentation generated successfully: {OUTPUT_PPTX}")

if __name__ == "__main__":
    create_presentation()
