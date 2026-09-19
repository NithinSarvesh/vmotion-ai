"""
VMotion AI — DA1 Presentation Generator
Generates a professional 18-slide PowerPoint presentation (.pptx) adhering to academic rigor,
high-density visual hierarchy, clean card layouts, and embedding actual project screenshots.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# --- Color Palette Constants ---
BG_COLOR = RGBColor(248, 249, 250)        # #F8F9FA Warm off-white
CARD_BG = RGBColor(255, 255, 255)         # #FFFFFF Pure white
CARD_BORDER = RGBColor(226, 232, 240)     # #E2E8F0 Hairline slate
TEXT_PRIMARY = RGBColor(15, 23, 42)       # #0F172A Slate 900
TEXT_SECONDARY = RGBColor(71, 85, 105)    # #475569 Slate 600
TEXT_MUTED = RGBColor(148, 163, 184)      # #94A3B8 Slate 400
ACCENT_BLUE = RGBColor(37, 99, 235)       # #2563EB Electric Blue
ACCENT_INDIGO = RGBColor(99, 102, 241)    # #6366F1 Modern Indigo
ACCENT_EMERALD = RGBColor(16, 185, 129)   # #10B981 Emerald Green
ACCENT_AMBER = RGBColor(245, 158, 11)     # #F59E0B Amber
ACCENT_RED = RGBColor(239, 68, 68)        # #EF4444 Crimson Red
PILL_BG = RGBColor(241, 245, 249)         # #F1F5F9 Slate 100

SCREENSHOTS_DIR = r"d:\projects\vmotion ai\VMotion_AI_DA1_Screenshots"
OUTPUT_PPTX = r"d:\projects\vmotion ai\VMotion_AI_DA1_Presentation.pptx"

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]  # Blank layout

    def add_base_slide(chapter_tag, title_text, subtitle_text=""):
        slide = prs.slides.add_slide(blank_layout)
        
        # Background fill
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()

        # Top Header Bar Card
        header_card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.0))
        header_card.fill.solid()
        header_card.fill.fore_color.rgb = CARD_BG
        header_card.line.color.rgb = CARD_BORDER
        header_card.line.width = Pt(1)

        # Header Text Frame
        tf = header_card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.3)
        tf.margin_top = Inches(0.12)
        tf.margin_right = Inches(0.3)
        tf.margin_bottom = Inches(0.1)

        # Paragraph 1: Tag & Subtitle
        p1 = tf.paragraphs[0]
        p1.text = chapter_tag.upper()
        p1.font.name = "Arial"
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_BLUE

        # Paragraph 2: Main Slide Title
        p2 = tf.add_paragraph()
        p2.text = title_text
        p2.font.name = "Arial"
        p2.font.size = Pt(18)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_PRIMARY

        # Footer Meta
        footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
        ftf = footer_box.text_frame
        ftf.margin_top = Inches(0)
        ftf.margin_bottom = Inches(0)
        ftf.margin_left = Inches(0)
        ftf.margin_right = Inches(0)
        fp = ftf.paragraphs[0]
        fp.text = "VMotion AI • Digital Assignment 1 (DA1) • B.Tech Computer Science & Engineering • VIT Vellore"
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
            tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.4))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title.upper()
            p.font.name = "Arial"
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = BG_COLOR
    bg1.line.fill.background()

    # Main Hero Card
    main_hero = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(0.8), Inches(10.933), Inches(5.9))
    main_hero.fill.solid()
    main_hero.fill.fore_color.rgb = CARD_BG
    main_hero.line.color.rgb = CARD_BORDER
    main_hero.line.width = Pt(1.5)

    # Content inside hero
    hero_tf = main_hero.text_frame
    hero_tf.word_wrap = True
    hero_tf.margin_left = Inches(0.8)
    hero_tf.margin_right = Inches(0.8)
    hero_tf.margin_top = Inches(0.6)

    p = hero_tf.paragraphs[0]
    p.text = "ACADEMIC CAPSTONE EVALUATION • DIGITAL ASSIGNMENT 1 (DA1)"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE

    p = hero_tf.add_paragraph()
    p.text = "VMotion AI"
    p.font.name = "Arial"
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = TEXT_PRIMARY
    p.space_after = Pt(8)

    p = hero_tf.add_paragraph()
    p.text = "Intelligent Virtual Machine Migration Control Plane using Deep Reinforcement Learning (MaskablePPO) & Deterministic Safety Controls"
    p.font.name = "Arial"
    p.font.size = Pt(15)
    p.font.color.rgb = TEXT_SECONDARY
    p.space_after = Pt(28)

    # Metadata Grid in Title Slide
    meta_box = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2.0), Inches(3.6), Inches(9.333), Inches(2.4))
    meta_box.fill.solid()
    meta_box.fill.fore_color.rgb = PILL_BG
    meta_box.line.color.rgb = CARD_BORDER
    meta_box.line.width = Pt(1)

    mtf = meta_box.text_frame
    mtf.word_wrap = True
    mtf.margin_left = Inches(0.4)
    mtf.margin_right = Inches(0.4)
    mtf.margin_top = Inches(0.3)

    p = mtf.paragraphs[0]
    p.text = "CANDIDATE & ACADEMIC CREDENTIALS"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = TEXT_PRIMARY

    p = mtf.add_paragraph()
    p.text = "Student Name: Nithin Sarvesh M  |  Email: nithinsarvesh.m2025@vitstudent.ac.in"
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE

    p = mtf.add_paragraph()
    p.text = "Degree / Program: B.Tech in Computer Science and Engineering"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_SECONDARY

    p = mtf.add_paragraph()
    p.text = "Department: School of Computer Science and Engineering (SCOPE)"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_SECONDARY

    p = mtf.add_paragraph()
    p.text = "Institution: Vellore Institute of Technology (VIT), Vellore, Tamil Nadu, India"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_SECONDARY

    p = mtf.add_paragraph()
    p.text = "Artifact Verification: Git Tag v1.0.1-rc1 (Commit 3d5c7ab)  |  Model: PPO V5 (SHA-256: bc47c2a5...)"
    p.font.name = "Arial"
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT
    # =========================================================================
    s2 = add_base_slide("01 // PROBLEM DEFINITION", "Problem Statement: Dynamic Imbalance in Multi-Tenant Hypervisors")
    
    # 3 Column Cards
    col_w = Inches(3.75)
    gap = Inches(0.24)
    left_start = Inches(0.8)
    top_pos = Inches(1.6)
    card_h = Inches(5.2)

    # Card 1: The Virtualization Dilemma
    c1 = add_card(s2, left_start, top_pos, col_w, card_h, "1. Dynamic Infrastructure Skew")
    tf1 = c1.text_frame
    tf1.margin_top = Inches(0.6)
    tf1.margin_left = tf1.margin_right = Inches(0.25)
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Cloud hypervisors experience volatile, non-linear workload fluctuations that produce severe resource contention."
    p.font.size = Pt(12); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(12)
    p = tf1.add_paragraph()
    p.text = "• CPU & RAM Hotspots: Asymmetric demand leaves some physical hosts throttled (>85% CPU) while adjacent nodes remain idle."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(8)
    p = tf1.add_paragraph()
    p.text = "• Cascading SLA Breaches: High-priority customer services suffer latency spikes and memory starvation when co-located with noisy neighbors."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(8)
    p = tf1.add_paragraph()
    p.text = "• Energy & Compute Waste: Unbalanced clusters consume peak dynamic power without delivering fair throughput."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY

    # Card 2: Failure of Static Heuristics
    c2 = add_card(s2, left_start + col_w + gap, top_pos, col_w, card_h, "2. Limits of Static Heuristics")
    tf2 = c2.text_frame
    tf2.margin_top = Inches(0.6)
    tf2.margin_left = tf2.margin_right = Inches(0.25)
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Commercial platforms rely on threshold-based rule engines (e.g. migrate when CPU > 80%) with critical deficiencies:"
    p.font.size = Pt(12); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(12)
    p = tf2.add_paragraph()
    p.text = "• Migration Thrashing: Threshold crossing triggers immediate migrations that ping-pong workloads back and forth continuously."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(8)
    p = tf2.add_paragraph()
    p.text = "• Blind Destination Picking: Greedy algorithms shift loads to targets that quickly overload upon arrival."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(8)
    p = tf2.add_paragraph()
    p.text = "• Manual Operator Bottleneck: Human administrators cannot respond within seconds to rapid transient spikes."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY

    # Card 3: Academic Problem Statement
    c3 = add_card(s2, left_start + (col_w + gap)*2, top_pos, col_w, card_h, "3. Academic Problem Statement", border_color=ACCENT_BLUE)
    tf3 = c3.text_frame
    tf3.margin_top = Inches(0.6)
    tf3.margin_left = tf3.margin_right = Inches(0.25)
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "FORMAL STATEMENT:"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(8)
    p = tf3.add_paragraph()
    p.text = "\"Design and implement an autonomous hypervisor control plane that continuously optimizes multi-host live migration using Deep Reinforcement Learning (PPO) while guaranteeing that statistical AI models cannot execute unsafe infrastructure commands.\""
    p.font.size = Pt(12); p.font.italic = True; p.font.color.rgb = TEXT_PRIMARY; p.space_after = Pt(14)
    p = tf3.add_paragraph()
    p.text = "Mandatory Invariants:\n1. 103-Dimensional Telemetry State Encoding\n2. Discrete(7) Action Space with Cooldown Masking\n3. Deterministic 8-Rule Fail-Closed Safety Gate\n4. Two-Phase Human Operator Governance\n5. Post-Migration Verification & Guest Ping"
    p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 3: MOTIVATION & SIGNIFICANCE
    # =========================================================================
    s3 = add_base_slide("02 // MOTIVATION & RESEARCH CONTEXT", "Motivation: Autonomous Optimization Meets Infrastructure Reliability")
    
    # 4 Quadrant Grid
    quad_w = Inches(5.7)
    quad_h = Inches(2.45)
    q_gap_x = Inches(0.33)
    q_gap_y = Inches(0.25)

    # Quad 1: Workload Volatility & Cloud Scale
    q1 = add_card(s3, Inches(0.8), Inches(1.6), quad_w, quad_h, "1. Volatile Multi-Tenant Cloud Environments")
    qtf1 = q1.text_frame; qtf1.margin_top = Inches(0.5); qtf1.margin_left = Inches(0.2); qtf1.word_wrap = True
    p = qtf1.paragraphs[0]
    p.text = "Modern cloud datacenters host diverse containers and VMs running bursty web apps, database transactions, and batch analytics. Static scheduling heuristics cannot anticipate non-linear correlation across multi-dimensional CPU, RAM, and Network dimensions."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY

    # Quad 2: Live Migration Feasibility
    q2 = add_card(s3, Inches(0.8) + quad_w + q_gap_x, Inches(1.6), quad_w, quad_h, "2. Live Migration as an Active Control Vector")
    qtf2 = q2.text_frame; qtf2.margin_top = Inches(0.5); qtf2.margin_left = Inches(0.2); qtf2.word_wrap = True
    p = qtf2.paragraphs[0]
    p.text = "QEMU/KVM pre-copy live migration allows transparent relocation of running virtual machines with milliseconds of downtime. However, each migration incurs transient hypervisor dirty-memory synchronization and interconnect bandwidth overhead that must be strategically timed."
    p.font.size = Pt(11); qtf2.word_wrap = True; p.font.color.rgb = TEXT_SECONDARY

    # Quad 3: Reinforcement Learning Potential
    q3 = add_card(s3, Inches(0.8), Inches(1.6) + quad_h + q_gap_y, quad_w, quad_h, "3. Deep Reinforcement Learning for Dynamic Systems")
    qtf3 = q3.text_frame; qtf3.margin_top = Inches(0.5); qtf3.margin_left = Inches(0.2); qtf3.word_wrap = True
    p = qtf3.paragraphs[0]
    p.text = "Proximal Policy Optimization (PPO) can learn non-linear policies that maximize long-term cumulative cluster balance rather than making myopic greedy decisions. By factoring Jain's Fairness Index and SLA violation penalties, PPO maintains cluster equilibrium."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY

    # Quad 4: The Critical Safety Gap
    q4 = add_card(s3, Inches(0.8) + quad_w + q_gap_x, Inches(1.6) + quad_h + q_gap_y, quad_w, quad_h, "4. The Critical Safety Gap in Autonomous Cloud Systems", border_color=ACCENT_RED)
    qtf4 = q4.text_frame; qtf4.margin_top = Inches(0.5); qtf4.margin_left = Inches(0.2); qtf4.word_wrap = True
    p = qtf4.paragraphs[0]
    p.text = "Deep RL agents are statistical black boxes prone to out-of-distribution hallucinations. Direct hypervisor access would allow an RL model to crash nodes or saturate memory. VMotion AI bridges this gap with a decoupled, fail-closed deterministic safety gate."
    p.font.size = Pt(11); p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 4: OBJECTIVES
    # =========================================================================
    s4 = add_base_slide("03 // PROJECT OBJECTIVES", "Measurable Engineering Objectives")
    
    # Left Card: Core Objectives
    lo_card = add_card(s4, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2), "Verified Functional Objectives")
    lotf = lo_card.text_frame; lotf.margin_top = Inches(0.55); lotf.margin_left = Inches(0.3); lotf.word_wrap = True
    
    objectives = [
        ("1. High-Density Telemetry Extraction", "Capture live multi-node CPU, RAM, Network RX/TX, Disk IO, and per-VM operational state into a structured schema."),
        ("2. Mathematical 103-Dimensional Adapter", "Design and verify a continuous normalized observation vector in [-1.0, 1.0] capturing node state, VM metrics, and global fairness."),
        ("3. PPO Policy Training & Collapse Resolution", "Train MaskablePPO over Discrete(7) action space, diagnosing and resolving training-distribution collapse via balanced 4-scenario sampling."),
        ("4. Deterministic 8-Rule Safety Gate", "Implement a fail-closed gate verifying VM running state, target distinctness, host health, memory headroom (120%), CPU ceiling (85%), quorum, and cooldown."),
        ("5. Human-in-the-Loop Governance", "Implement an operator authorization barrier requiring manual cryptographic/session approval before hypervisor dispatch."),
        ("6. Proxmox VE REST API v2 Integration", "Engineer a native async HTTP provider interfacing directly with Proxmox 9.x APIs, UPID polling, and QEMU guest-agent ping."),
        ("7. 12-State Migration Finite State Machine", "Implement strict progressive (RECOMMENDED -> VERIFIED) and terminal state transitions with post-placement assertion.")
    ]
    
    for i, (head, body) in enumerate(objectives):
        p = lotf.add_paragraph() if i > 0 else lotf.paragraphs[0]
        p.text = head
        p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = TEXT_PRIMARY
        p2 = lotf.add_paragraph()
        p2.text = body
        p2.font.size = Pt(10); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(4)

    # Right Card: Academic Constraints
    ro_card = add_card(s4, Inches(8.55), Inches(1.6), Inches(3.98), Inches(5.2), "Academic Ground Rules & Invariants", border_color=ACCENT_INDIGO)
    rotf = ro_card.text_frame; rotf.margin_top = Inches(0.55); rotf.margin_left = Inches(0.25); rotf.word_wrap = True
    
    rules = [
        ("Zero Hallucinated Claims", "Distinguish strictly between code implemented, simulation tested, and physical hardware verified."),
        ("Frozen Artifact Integrity", "Candidate PPO V5 model locked with verified SHA-256: bc47c2a564d2..."),
        ("No Direct Hypervisor Access", "Frontend and PPO never communicate directly with hypervisors; mediated entirely by backend safety gate."),
        ("No Silent Fallbacks", "Live mode must never silently fall back to simulation data if hypervisors are unreachable."),
        ("Strict Fail-Closed Logic", "Any ambiguous, offline, or unvalidated state immediately aborts migration proposals.")
    ]
    for i, (head, body) in enumerate(rules):
        p = rotf.add_paragraph() if i > 0 else rotf.paragraphs[0]
        p.text = f"• {head}"
        p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_INDIGO
        p2 = rotf.add_paragraph()
        p2.text = body
        p2.font.size = Pt(10); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(6)

    # =========================================================================
    # SLIDE 5: EXISTING SYSTEM vs PROPOSED SYSTEM
    # =========================================================================
    s5 = add_base_slide("04 // ARCHITECTURAL COMPARISON", "Existing Solutions vs. VMotion AI Proposed Architecture")

    # Table layout
    table_shape = s5.shapes.add_table(8, 3, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.2))
    table = table_shape.table
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(4.7)
    table.columns[2].width = Inches(4.733)

    headers = ["Evaluation Dimension", "Traditional / Static Systems (VMware DRS / Heuristics)", "Proposed VMotion AI Architecture"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_PRIMARY
        p = cell.text_frame.paragraphs[0]
        p.text = h; p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = RGBColor(255, 255, 255)

    comparisons = [
        ("Decision Mechanism", "Static threshold triggers (e.g. CPU > 80%) or greedy local optimization heuristics.", "Deep Reinforcement Learning (MaskablePPO) optimizing multi-step cluster equilibrium."),
        ("Telemetry Awareness", "Single-metric or uncoupled host CPU/RAM metrics; ignores cluster-wide variance.", "103-Dimensional Continuous State Vector including Jain's Fairness, node headroom, and SLA weights."),
        ("Migration Flapping", "Frequent threshold-crossing leads to rapid ping-ponging and thrashing across hosts.", "Mathematical 60-second cooldown policy dynamically enforced via Invalid Action Masking."),
        ("Safety & Reliability", "Rule engines execute directly on hypervisors; catastrophic failures if assumptions fail.", "Decoupled Deterministic 8-Rule Safety Gate with fail-closed verification before dispatch."),
        ("Governance Model", "Binary choice: completely manual ticket requests or unmonitored automated execution.", "Dual-Mode Architecture: Stage 03 Operator Gate requires explicit human signoff by default."),
        ("Execution Verification", "Fire-and-forget: command dispatch is assumed to equal successful migration.", "Formal 12-State FSM actively querying destination host residency and QEMU guest-agent ping."),
        ("Hypervisor Abstraction", "Tightly coupled to proprietary hypervisors (VMware vCenter / vSphere APIs).", "Extensible Provider Abstraction supporting high-fidelity Simulation and Proxmox VE 9.x REST.")
    ]

    for row_idx, (dim, exist, prop) in enumerate(comparisons, start=1):
        c0 = table.cell(row_idx, 0)
        c0.fill.solid(); c0.fill.fore_color.rgb = PILL_BG
        p0 = c0.text_frame.paragraphs[0]
        p0.text = dim; p0.font.bold = True; p0.font.size = Pt(10); p0.font.color.rgb = TEXT_PRIMARY

        c1 = table.cell(row_idx, 1)
        c1.fill.solid(); c1.fill.fore_color.rgb = CARD_BG
        p1 = c1.text_frame.paragraphs[0]
        p1.text = exist; p1.font.size = Pt(9.5); p1.font.color.rgb = TEXT_SECONDARY

        c2 = table.cell(row_idx, 2)
        c2.fill.solid(); c2.fill.fore_color.rgb = CARD_BG
        p2 = c2.text_frame.paragraphs[0]
        p2.text = prop; p2.font.size = Pt(9.5); p2.font.bold = True; p2.font.color.rgb = ACCENT_BLUE

    # =========================================================================
    # SLIDE 6: SYSTEM ARCHITECTURE
    # =========================================================================
    s6 = add_base_slide("05 // SYSTEM ARCHITECTURE", "Decoupled Multi-Tier System Architecture")

    # 4 Tier Boxes arranged vertically with flow
    tier_w = Inches(11.733)
    tier_h = Inches(1.1)
    tier_y = Inches(1.6)
    spacing = Inches(1.28)

    tiers = [
        ("TIER 1: PHYSICAL & SIMULATED INFRASTRUCTURE LAYER", 
         "Proxmox VE 9.x Hypervisors (Debian 12/KVM)  |  High-Fidelity Simulation Provider (Dynamic CPU Drift & Memory Dirtying)",
         "Interfaces: HTTPS REST API v2 (Port 8006), Corosync Cluster Network (UDP 5405-5412), Live Migration Stream (TCP 60000-60050)", ACCENT_BLUE),
        
        ("TIER 2: TELEMETRY INGESTION & 103-DIMENSIONAL FEATURE ADAPTER",
         "Rolling Metric Buffer  |  Jain's Fairness Calculator  |  Vector Normalizer ([-1.0, 1.0] Bounds)  |  Dynamic Action Mask Generator",
         "Extracts 24 Node Features (0..23) + 60 VM Features (24..83) + 19 Global/Fairness Features (84..102) every 2.0 seconds", ACCENT_INDIGO),

        ("TIER 3: REINFORCEMENT LEARNING INFERENCE & DETERMINISTIC SAFETY GATE",
         "Frozen PPO V5 Actor-Critic Policy (SHA-256: bc47c2a5...)  |  Heuristic Fallback  |  Deterministic 8-Rule Fail-Closed Gate",
         "The AI generates candidate action over Discrete(7); Safety Gate evaluates 8 physical rules and unconditionally blocks unsafe proposals", ACCENT_AMBER),

        ("TIER 4: HUMAN GOVERNANCE, 12-STATE FSM ORCHESTRATOR & CONTROL PLANE UI",
         "Stage 03 Operator Approval Gate  |  UPID Task Poller  |  QEMU Guest-Agent Health Checker  |  Three.js 3D WebGL Frontend",
         "Enforces operator signoff, tracks migration state, queries destination residency, and renders append-only forensic audit trail", ACCENT_EMERALD)
    ]

    for i, (t_title, t_main, t_sub, t_color) in enumerate(tiers):
        t_card = add_card(s6, Inches(0.8), tier_y + i*spacing, tier_w, tier_h, border_color=t_color)
        ttf = t_card.text_frame
        ttf.margin_top = Inches(0.12); ttf.margin_left = Inches(0.3); ttf.word_wrap = True
        
        p0 = ttf.paragraphs[0]
        p0.text = t_title
        p0.font.bold = True; p0.font.size = Pt(11); p0.font.color.rgb = t_color
        
        p1 = ttf.add_paragraph()
        p1.text = t_main
        p1.font.bold = True; p1.font.size = Pt(11); p1.font.color.rgb = TEXT_PRIMARY
        
        p2 = ttf.add_paragraph()
        p2.text = t_sub
        p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 7: END-TO-END WORKFLOW
    # =========================================================================
    s7 = add_base_slide("06 // SYSTEM WORKFLOW", "End-to-End Autonomous Migration Lifecycle Flowchart")

    # Process Flow Cards in 2 rows of 4 cards
    card_w = Inches(2.75)
    card_h = Inches(2.4)
    gap_x = Inches(0.24)
    gap_y = Inches(0.24)
    start_x = Inches(0.8)

    flow_steps = [
        ("Step 01: Telemetry Sampling", "Collector queries active hypervisor nodes or simulation engine every 2s for CPU, RAM, Disk, and Net IO.", ACCENT_BLUE),
        ("Step 02: 103-Dim Normalization", "Raw metrics transformed into bounded floats [-1.0, 1.0]. Jain's fairness and load variances computed.", ACCENT_BLUE),
        ("Step 03: Action Masking", "Calculates valid action mask: disables VMs in active 60s cooldown or stopped states (Discrete 7).", ACCENT_INDIGO),
        ("Step 04: PPO Policy Inference", "Frozen PPO V5 evaluates observation vector; outputs softmax selection probabilities across actions.", ACCENT_INDIGO),
        ("Step 05: Destination Placement", "Deterministic load-gradient resolver identifies destination node with highest resource headroom.", ACCENT_AMBER),
        ("Step 06: 8-Rule Safety Audit", "Safety gate evaluates target CPU (<85%), RAM (120%), distinct host, host health, and quorum. Fail-closed.", ACCENT_AMBER),
        ("Step 07: Human Operator Signoff", "Proposal queued in Stage 03 Operator Gate; requires explicit operator approval before dispatch.", ACCENT_EMERALD),
        ("Step 08: Dispatch & Verification", "Dispatches POST /migrate; streams UPID; asserts destination placement and pings QEMU guest-agent.", ACCENT_EMERALD)
    ]

    for i, (title, body, color) in enumerate(flow_steps):
        row = i // 4
        col = i % 4
        x = start_x + col * (card_w + gap_x)
        y = Inches(1.6) + row * (card_h + gap_y)

        c = add_card(s7, x, y, card_w, card_h, border_color=color)
        ctf = c.text_frame
        ctf.margin_top = Inches(0.2); ctf.margin_left = Inches(0.2); ctf.margin_right = Inches(0.2); ctf.word_wrap = True
        
        p0 = ctf.paragraphs[0]
        p0.text = title
        p0.font.bold = True; p0.font.size = Pt(11); p0.font.color.rgb = color; p0.space_after = Pt(8)
        
        p1 = ctf.add_paragraph()
        p1.text = body
        p1.font.size = Pt(10); p1.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 8: DETAILED MODULE BREAKDOWN
    # =========================================================================
    s8 = add_base_slide("07 // IMPLEMENTATION MODULES", "Core Repository Modules & Implementation Status")

    # Table of 8 modules
    table_shape8 = s8.shapes.add_table(9, 4, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.2))
    table8 = table_shape8.table
    table8.columns[0].width = Inches(2.2)
    table8.columns[1].width = Inches(3.2)
    table8.columns[2].width = Inches(4.533)
    table8.columns[3].width = Inches(1.8)

    headers8 = ["Module Name", "Repository Files", "Architectural Role & Functionality", "Status"]
    for col_idx, h in enumerate(headers8):
        cell = table8.cell(0, col_idx)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_PRIMARY
        p = cell.text_frame.paragraphs[0]
        p.text = h; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = RGBColor(255, 255, 255)

    modules_data = [
        ("Telemetry & Collector", "backend/app/telemetry/collector.py", "Background polling of node/VM metrics; rolling CPU/RAM buffer; Jain's index.", "COMPLETE (100%)"),
        ("103-Dim Feature Adapter", "backend/app/adapter/observation.py", "Extracts exact 103 continuous normalized features; bounded [-1, 1]; schema v1.0.0.", "COMPLETE (100%)"),
        ("PPO Decision Engine", "backend/app/engine/ppo_engine.py", "sb3-contrib MaskablePPO inference; softmax probability extraction; baseline fallback.", "FROZEN V5 (100%)"),
        ("Deterministic Safety Gate", "backend/app/safety/gate.py", "8 mandatory physical checks; fail-closed audit; active migration lock manager.", "COMPLETE (100%)"),
        ("Migration FSM Planner", "backend/app/planner/planner.py", "12-state FSM; human approval gate; UPID polling; post-placement verification.", "COMPLETE (100%)"),
        ("Provider Abstraction", "backend/app/providers/base.py", "BaseVirtualizationProvider abstract contract; ClusterState and MigrationPlan types.", "COMPLETE (100%)"),
        ("Proxmox VE Provider", "backend/app/providers/proxmox.py", "Proxmox REST API v2 client; UPID streaming; QEMU guest agent ping; token auth.", "MOCK TESTED (75%)"),
        ("Frontend Control Plane", "frontend/src/ (React 19 + 3D)", "Three.js WebGL spatial cluster, Lenis smooth scrolling, 6-section control console.", "COMPLETE (100%)")
    ]

    for row_idx, (m_name, m_file, m_role, m_stat) in enumerate(modules_data, start=1):
        c0 = table8.cell(row_idx, 0); c0.fill.solid(); c0.fill.fore_color.rgb = PILL_BG
        p0 = c0.text_frame.paragraphs[0]; p0.text = m_name; p0.font.bold = True; p0.font.size = Pt(9.5); p0.font.color.rgb = TEXT_PRIMARY

        c1 = table8.cell(row_idx, 1); c1.fill.solid(); c1.fill.fore_color.rgb = CARD_BG
        p1 = c1.text_frame.paragraphs[0]; p1.text = m_file; p1.font.size = Pt(8.5); p1.font.color.rgb = ACCENT_INDIGO

        c2 = table8.cell(row_idx, 2); c2.fill.solid(); c2.fill.fore_color.rgb = CARD_BG
        p2 = c2.text_frame.paragraphs[0]; p2.text = m_role; p2.font.size = Pt(9); p2.font.color.rgb = TEXT_SECONDARY

        c3 = table8.cell(row_idx, 3); c3.fill.solid(); c3.fill.fore_color.rgb = CARD_BG
        p3 = c3.text_frame.paragraphs[0]; p3.text = m_stat; p3.font.bold = True; p3.font.size = Pt(8.5)
        p3.font.color.rgb = ACCENT_EMERALD if "COMPLETE" in m_stat or "FROZEN" in m_stat else ACCENT_AMBER

    # =========================================================================
    # SLIDE 9: REINFORCEMENT LEARNING FORMULATION
    # =========================================================================
    s9 = add_base_slide("08 // REINFORCEMENT LEARNING", "PPO Formulation: State, Action, Masking & Multi-Objective Reward")

    col_w9 = Inches(5.7)
    card_h9 = Inches(5.2)

    # Left Column: State & Action Space
    cl9 = add_card(s9, Inches(0.8), Inches(1.6), col_w9, card_h9, "Observation & Action Formalism")
    ltf9 = cl9.text_frame; ltf9.margin_top = Inches(0.55); ltf9.margin_left = Inches(0.3); ltf9.word_wrap = True
    
    p = ltf9.paragraphs[0]; p.text = "103-DIMENSIONAL STATE VECTOR (S in [-1.0, 1.0]^103)"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(4)
    p = ltf9.add_paragraph()
    p.text = "• Block 1 [0..23]: 3 Compute Nodes x 8 features each (CPU util, RAM util, Net RX/TX, Disk util, VM density, Status flag, Headroom).\n• Block 2 [24..83]: 6 Workload slots x 10 features each (CPU util, RAM alloc, RAM util, Net IO, SLA weight, Cooldown, Mig count, Uptime, Contention, Host index).\n• Block 3 [84..102]: 19 Global metrics (Jain's CPU/RAM fairness, cluster std dev, power index, SLA breach ratio, storage status, quorum)."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(12)

    p = ltf9.add_paragraph(); p.text = "DISCRETE(7) ACTION SPACE & ACTION MASKING"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(4)
    p = ltf9.add_paragraph()
    p.text = "• Action 0: No-Op (Maintain cluster status quo).\n• Actions 1..6: Select candidate VM [0..5] for live migration.\n• Destination Resolution: Decoupled from PPO; determined by deterministic headroom-gradient placement logic.\n• Invalid Action Mask: Dynamic boolean vector disabling actions where VM is in active 60s cooldown or in stopped state."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    # Right Column: Reward Function Formulation
    cr9 = add_card(s9, Inches(6.833), Inches(1.6), col_w9, card_h9, "Multi-Objective Reward Formulation", border_color=ACCENT_INDIGO)
    rtf9 = cr9.text_frame; rtf9.margin_top = Inches(0.55); rtf9.margin_left = Inches(0.3); rtf9.word_wrap = True

    p = rtf9.paragraphs[0]; p.text = "PER-STEP REWARD FUNCTION:"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_INDIGO; p.space_after = Pt(4)
    p = rtf9.add_paragraph()
    p.text = "R_t = R_balance + R_stability - P_SLA - P_overload - P_migration - P_invalid"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = TEXT_PRIMARY; p.space_after = Pt(10)

    reward_items = [
        ("1. Load Balance Dividend (R_balance)", "2.5 * Jain_CPU - 1.5 * Std_CPU (Rewards uniform cluster compute distribution)."),
        ("2. Stability Bonus (R_stability)", "+1.0 if Action == No-Op and Std_CPU < 0.12 (Prevents unnecessary migration flapping)."),
        ("3. SLA Breach Penalty (P_SLA)", "-2.0 per breached workload (Penalizes workloads exceeding contractual SLA ceilings)."),
        ("4. Overload Penalty (P_overload)", "-4.0 per host operating above 85% CPU capacity (Strict host exhaustion barrier)."),
        ("5. Migration Transient Cost (P_migration)", "-0.8 per active migration (Accounts for memory dirtying and link bandwidth)."),
        ("6. Invalid Action Penalty (P_invalid)", "-10.0 if masked action attempted (Strict policy constraint enforcement).")
    ]
    for head, body in reward_items:
        p = rtf9.add_paragraph(); p.text = head; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_PRIMARY
        p2 = rtf9.add_paragraph(); p2.text = body; p2.font.size = Pt(9); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(3)

    # =========================================================================
    # SLIDE 10: PPO TRAINING EVOLUTION (V4 vs V5)
    # =========================================================================
    s10 = add_base_slide("09 // EMPIRICAL RL RESULTS", "PPO Training Evolution: Diagnosing & Fixing Training Distribution Collapse")

    # Table of verified benchmark results (600 episodes)
    table_shape10 = s10.shapes.add_table(6, 6, Inches(0.8), Inches(1.6), Inches(11.733), Inches(3.2))
    table10 = table_shape10.table
    table10.columns[0].width = Inches(2.733)
    table10.columns[1].width = Inches(1.8)
    table10.columns[2].width = Inches(1.8)
    table10.columns[3].width = Inches(1.8)
    table10.columns[4].width = Inches(1.8)
    table10.columns[5].width = Inches(1.8)

    headers10 = ["Benchmark Metric", "Baseline Rule", "Random Masked", "PPO V4 (Collapse)", "PPO V5 (Balanced)", "V4 -> V5 Delta"]
    for col_idx, h in enumerate(headers10):
        cell = table10.cell(0, col_idx)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_PRIMARY
        p = cell.text_frame.paragraphs[0]
        p.text = h; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = RGBColor(255, 255, 255)

    benchmark_data = [
        ("Overall Mean Reward", "-122.54", "-89.25", "-263.48", "+55.81", "+319.29 pts"),
        ("Unseen Test Split Reward", "+115.37", "+53.28", "-53.16", "+154.93", "+208.09 pts"),
        ("Mean Migrations / Episode", "14.79", "73.11", "0.00 (Collapsed)", "2.07 (Targeted)", "+2.07 migs"),
        ("Mean Overload Steps / Ep", "6.68", "16.93", "60.22", "7.33", "-52.89 steps (-87.8%)"),
        ("Final Jain's Fairness Index", "0.9610", "0.8944", "0.7682", "0.9288", "+0.1606 (+20.9%)")
    ]

    for row_idx, row in enumerate(benchmark_data, start=1):
        for col_idx, val in enumerate(row):
            cell = table10.cell(row_idx, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = PILL_BG if col_idx == 0 else (CARD_BG if col_idx < 4 else (RGBColor(240, 253, 244) if col_idx == 4 else RGBColor(238, 242, 255)))
            p = cell.text_frame.paragraphs[0]
            p.text = val; p.font.size = Pt(9.5)
            if col_idx in [0, 4, 5]:
                p.font.bold = True
            p.font.color.rgb = ACCENT_EMERALD if col_idx in [4, 5] else (ACCENT_RED if col_idx == 3 and "Collapse" in val else TEXT_PRIMARY)

    # Narrative Diagnosis Card below table
    diag_card = add_card(s10, Inches(0.8), Inches(5.05), Inches(11.733), Inches(1.75), "Empirical Diagnosis: Why V4 Collapsed and How V5 Succeeded")
    dtf = diag_card.text_frame; dtf.margin_top = Inches(0.4); dtf.margin_left = Inches(0.3); dtf.word_wrap = True
    p = dtf.paragraphs[0]
    p.text = "• The V4 Failure Mode: PPO V4 was trained on 100% 'NORMAL' cluster conditions. In nominal states, any migration incurs a transient penalty (-0.8); thus, the policy learned that Action 0 (No-Op) was globally optimal, collapsing into zero migrations during critical hotspot states."
    p.font.size = Pt(9.5); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(4)
    p = dtf.add_paragraph()
    p.text = "• The V5 Resolution: Introduced a balanced training sampler across 4 distinct regimes: NORMAL (25%), CPU_HOTSPOT (25%), RAM_HOTSPOT (25%), and MIXED_OVERLOAD (25%). Exposure to high contention taught PPO V5 that the rebalancing dividend (+2.5 Jain's) far exceeds transient costs, achieving +154.93 on unseen test scenarios."
    p.font.size = Pt(9.5); p.font.bold = True; p.font.color.rgb = ACCENT_BLUE

    # =========================================================================
    # SLIDE 11: DETERMINISTIC SAFETY ENGINE
    # =========================================================================
    s11 = add_base_slide("10 // DETERMINISTIC SAFETY GATE", "The Deterministic Safety Gate: 8 Mandatory Physical Invariants")

    # 8 Rules in 2 Columns of 4 Cards
    col_w11 = Inches(5.7)
    card_h11 = Inches(1.15)
    gap_y11 = Inches(0.15)

    rules_8 = [
        ("RULE 01: VM_RUNNING_STATE", "Target workload must exist and reside in operational 'running' hypervisor state.", ACCENT_EMERALD),
        ("RULE 02: DISTINCT_TARGET", "Source node and destination node must be distinct physical hypervisors (src != dest).", ACCENT_EMERALD),
        ("RULE 03: SOURCE_NODE_HEALTH", "Source hypervisor daemon reports active heartbeat and zero hardware alarms.", ACCENT_EMERALD),
        ("RULE 04: DEST_NODE_HEALTH", "Destination hypervisor daemon is online and responsive over cluster network fabric.", ACCENT_EMERALD),
        ("RULE 05: DEST_RAM_HEADROOM", "Destination unallocated RAM must exceed VM footprint + 20% safety margin.", ACCENT_EMERALD),
        ("RULE 06: DEST_CPU_CAPACITY", "Projected post-migration CPU utilization on target node must remain <= 85.0%.", ACCENT_EMERALD),
        ("RULE 07: STORAGE_AND_QUORUM", "Datastore access confirmed (shared NFS or local NBD mirror) & Corosync quorum active.", ACCENT_EMERALD),
        ("RULE 08: COOLDOWN_PERIOD", "Minimum 60-second cooldown elapsed since VM's last migration; no active lock.", ACCENT_EMERALD)
    ]

    for idx, (r_name, r_desc, r_col) in enumerate(rules_8):
        col_idx = idx // 4
        row_idx = idx % 4
        x = Inches(0.8) + col_idx * (col_w11 + Inches(0.33))
        y = Inches(1.6) + row_idx * (card_h11 + gap_y11)

        c = add_card(s11, x, y, col_w11, card_h11, border_color=CARD_BORDER)
        ctf = c.text_frame; ctf.margin_top = Inches(0.12); ctf.margin_left = Inches(0.25); ctf.word_wrap = True
        
        p = ctf.paragraphs[0]; p.text = r_name; p.font.bold = True; p.font.size = Pt(10.5); p.font.color.rgb = ACCENT_BLUE
        p2 = ctf.add_paragraph(); p2.text = r_desc; p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_SECONDARY

    # Fail-Closed Summary Box
    fc_box = s11.shapes.add_textbox(Inches(0.8), Inches(6.4), Inches(11.733), Inches(0.55))
    fctf = fc_box.text_frame; fctf.word_wrap = True; fctf.margin_left = Inches(0)
    p = fctf.paragraphs[0]
    p.text = "CORE ARCHITECTURAL GUARANTEE: The safety gate operates under strict FAIL-CLOSED semantics. If any single check fails, the migration proposal is unconditionally rejected with machine-readable rejection codes, overriding AI confidence."
    p.font.name = "Arial"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_RED

    # =========================================================================
    # SLIDE 12: PROXMOX VE HYPERVISOR INTEGRATION
    # =========================================================================
    s12 = add_base_slide("11 // HYPERVISOR INTEGRATION", "Proxmox VE 9.x Provider Architecture & Least-Privilege Protocol")

    left_w12 = Inches(6.8)
    right_w12 = Inches(4.65)
    card_h12 = Inches(5.2)

    # Left Card: Proxmox Technical Protocol
    c_px = add_card(s12, Inches(0.8), Inches(1.6), left_w12, card_h12, "Proxmox VE REST API v2 Integration Contract")
    pxtf = c_px.text_frame; pxtf.margin_top = Inches(0.55); pxtf.margin_left = Inches(0.3); pxtf.word_wrap = True

    px_points = [
        ("1. Target Hypervisor Release", "Proxmox VE 9.x / current supported release (currently 9.2), Debian 12 Bookworm, Linux 6.8+ kernel, x86_64 virtualization."),
        ("2. Privilege-Separated API Token", "Configured via: pveum user token add vmotion-api@pve automation -privsep 1. Authentication via HTTP header: PVEAPIToken=vmotion-api@pve!automation=SECRET."),
        ("3. Validated Minimum Privilege Set (PVE 9.x)", "Sys.Audit, VM.Audit, VM.Migrate, VM.Allocate, Datastore.Audit, Datastore.AllocateSpace, VM.GuestAgent.Audit. (Invalid VM.Monitor excised)."),
        ("4. Asynchronous UPID Task Polling", "Live migration dispatches POST /nodes/{node}/qemu/{vmid}/migrate returning a UPID string (UPID:node:pid:...); polled at 1.0s intervals."),
        ("5. Post-Migration Placement & Guest Ping", "Asserts VM no longer active on source; asserts active on destination; queries QEMU guest-agent ping (GET .../agent/ping) before marking VERIFIED."),
        ("6. Corosync & Migration Networking", "Cluster Corosync: UDP 5405-5412; Proxmox Web/API: TCP 8006; Live Migration Stream: TCP 60000-60050.")
    ]
    for head, body in px_points:
        p = pxtf.add_paragraph(); p.text = head; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_BLUE
        p2 = pxtf.add_paragraph(); p2.text = body; p2.font.size = Pt(9); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(4)

    # Right Card: Academic Verification Status
    c_st = add_card(s12, Inches(7.88), Inches(1.6), right_w12, card_h12, "Readiness & Verification Audit", border_color=ACCENT_AMBER)
    stf = c_st.text_frame; stf.margin_top = Inches(0.55); stf.margin_left = Inches(0.25); stf.word_wrap = True

    st_items = [
        ("REST API Client Implementation", "COMPLETE (100% Code in proxmox.py)"),
        ("Unit & Mock Test Suite", "COMPLETE (10 passing mock tests)"),
        ("Token Authentication & Headers", "COMPLETE (pveum privilege separation)"),
        ("UPID Task Parsing & Tracking", "COMPLETE (Regex & field validation)"),
        ("QEMU Guest-Agent Ping Logic", "COMPLETE (Async ping endpoint)"),
        ("Real Physical Hardware Execution", "NOT VERIFIED (Pending Lab Rack)"),
        ("2-Node Quorum Consideration", "Requires external QDevice (qnetd) for fault-tolerant 2-node lab cluster")
    ]
    for head, status in st_items:
        p = stf.add_paragraph(); p.text = f"• {head}:"; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = TEXT_PRIMARY
        p2 = stf.add_paragraph(); p2.text = f"  [{status}]"; p2.font.size = Pt(9); p2.space_after = Pt(5)
        p2.font.color.rgb = ACCENT_EMERALD if "COMPLETE" in status else ACCENT_AMBER

    # =========================================================================
    # SLIDE 13: USER INTERFACE (3D CONTROL PLANE)
    # =========================================================================
    s13 = add_base_slide("12 // CONTROL PLANE INTERFACE", "User Interface: Spatial 3D WebGL Console & Telemetry Stream")

    # Display 2 key screenshots with callouts
    # Screenshot 1: Hero & 3D Cluster (media_1789825432019.png -> 01_hero_spatial_overview.png)
    # Screenshot 2: AI Engine / Safety Gate (02_ai_engine_decision_pipeline.png or 03_deterministic_safety_gate.png)
    img1_path = os.path.join(SCREENSHOTS_DIR, "01_hero_spatial_overview.png")
    img2_path = os.path.join(SCREENSHOTS_DIR, "02_ai_engine_decision_pipeline.png")

    if os.path.exists(img1_path):
        s13.shapes.add_picture(img1_path, Inches(0.8), Inches(1.6), width=Inches(5.7))
    else:
        add_card(s13, Inches(0.8), Inches(1.6), Inches(5.7), Inches(3.8), "[SCREENSHOT: HERO & 3D CLUSTER]")

    if os.path.exists(img2_path):
        s13.shapes.add_picture(img2_path, Inches(6.833), Inches(1.6), width=Inches(5.7))
    else:
        add_card(s13, Inches(6.833), Inches(1.6), Inches(5.7), Inches(3.8), "[SCREENSHOT: AI DECISION ENGINE]")

    # Captions below screenshots
    cap1 = add_card(s13, Inches(0.8), Inches(5.0), Inches(5.7), Inches(1.8), "Figure 1: Spatial 3D Cluster & Overview")
    c1tf = cap1.text_frame; c1tf.margin_top = Inches(0.4); c1tf.margin_left = Inches(0.2); c1tf.word_wrap = True
    p = c1tf.paragraphs[0]
    p.text = "Features Three.js WebGL spatial cluster with real-time compute pedestals proportional to CPU load, orbiting VM chassis with SLA priority rings, central pulsing AI core, and live aggregate telemetry ribbon."
    p.font.size = Pt(9.5); p.font.color.rgb = TEXT_SECONDARY

    cap2 = add_card(s13, Inches(6.833), Inches(5.0), Inches(5.7), Inches(1.8), "Figure 2: AI Decision Pipeline & Schema Explorer")
    c2tf = cap2.text_frame; c2tf.margin_top = Inches(0.4); c2tf.margin_left = Inches(0.2); c2tf.word_wrap = True
    p = c2tf.paragraphs[0]
    p.text = "Displays live MaskablePPO recommendation, dynamic softmax selection probability (100% honest, not 'success probability'), frozen SHA-256 artifact card, and interactive 103-dimensional vector inspector."
    p.font.size = Pt(9.5); p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 14: IMPLEMENTATION STATUS & COMPLETION %
    # =========================================================================
    s14 = add_base_slide("13 // PROJECT PROGRESS & COMPLETION", "Defensible Implementation Completion Analysis")

    # Table of weighted completion
    table_shape14 = s14.shapes.add_table(10, 4, Inches(0.8), Inches(1.6), Inches(7.5), Inches(5.2))
    table14 = table_shape14.table
    table14.columns[0].width = Inches(2.8)
    table14.columns[1].width = Inches(1.2)
    table14.columns[2].width = Inches(1.5)
    table14.columns[3].width = Inches(2.0)

    headers14 = ["Subsystem / Component", "Weight", "Module Status", "Weighted Score"]
    for col_idx, h in enumerate(headers14):
        cell = table14.cell(0, col_idx)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEXT_PRIMARY
        p = cell.text_frame.paragraphs[0]
        p.text = h; p.font.bold = True; p.font.size = Pt(9.5); p.font.color.rgb = RGBColor(255, 255, 255)

    weights_data = [
        ("Architecture & Interface Contracts", "10%", "100% Complete", "10.0%"),
        ("Backend & Control Plane (FastAPI)", "15%", "100% Complete", "15.0%"),
        ("Telemetry & 103-Dim Observation", "10%", "100% Complete", "10.0%"),
        ("PPO / RL Engine (PPO V5 Frozen)", "15%", "100% Complete", "15.0%"),
        ("Safety Gate (8 Rules) & 12-State FSM", "15%", "100% Complete", "15.0%"),
        ("Hypervisor Provider Implementation", "10%", "75% Complete", "7.5%"),
        ("Frontend Control Plane (React/3D)", "10%", "100% Complete", "10.0%"),
        ("Automated Testing (96 Tests Passing)", "10%", "90% Complete", "9.0%"),
        ("Technical Documentation & Specs", "5%", "100% Complete", "5.0%")
    ]

    for row_idx, (comp, wt, stat, scr) in enumerate(weights_data, start=1):
        c0 = table14.cell(row_idx, 0); c0.fill.solid(); c0.fill.fore_color.rgb = PILL_BG
        p0 = c0.text_frame.paragraphs[0]; p0.text = comp; p0.font.bold = True; p0.font.size = Pt(9); p0.font.color.rgb = TEXT_PRIMARY

        c1 = table14.cell(row_idx, 1); c1.fill.solid(); c1.fill.fore_color.rgb = CARD_BG
        p1 = c1.text_frame.paragraphs[0]; p1.text = wt; p1.font.size = Pt(9); p1.font.color.rgb = TEXT_SECONDARY

        c2 = table14.cell(row_idx, 2); c2.fill.solid(); c2.fill.fore_color.rgb = CARD_BG
        p2 = c2.text_frame.paragraphs[0]; p2.text = stat; p2.font.size = Pt(9); p2.font.color.rgb = ACCENT_BLUE

        c3 = table14.cell(row_idx, 3); c3.fill.solid(); c3.fill.fore_color.rgb = CARD_BG
        p3 = c3.text_frame.paragraphs[0]; p3.text = scr; p3.font.bold = True; p3.font.size = Pt(9); p3.font.color.rgb = ACCENT_EMERALD

    # Right Card: The Two Numbers (Academic Honesty)
    c_score = add_card(s14, Inches(8.55), Inches(1.6), Inches(3.98), Inches(5.2), "The Two Numbers: Honest Evaluation", border_color=ACCENT_BLUE)
    sctf = c_score.text_frame; sctf.margin_top = Inches(0.55); sctf.margin_left = Inches(0.25); sctf.word_wrap = True

    p = sctf.paragraphs[0]; p.text = "1. SOFTWARE IMPLEMENTATION & SIMULATION READINESS:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_BLUE; p.space_after = Pt(2)
    p = sctf.add_paragraph(); p.text = "91.5%"
    p.font.bold = True; p.font.size = Pt(32); p.font.color.rgb = ACCENT_EMERALD; p.space_after = Pt(6)
    p = sctf.add_paragraph()
    p.text = "All architectural tiers, RL training, 103-dim vector normalization, deterministic 8-rule safety gate, 12-state FSM, FastAPI backend, 3D frontend, and 96 unit/integration tests are 100% functional."
    p.font.size = Pt(9.5); p.font.color.rgb = TEXT_SECONDARY; p.space_after = Pt(14)

    p = sctf.add_paragraph(); p.text = "2. PHYSICAL HARDWARE VALIDATION:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_AMBER; p.space_after = Pt(2)
    p = sctf.add_paragraph(); p.text = "15.0%"
    p.font.bold = True; p.font.size = Pt(32); p.font.color.rgb = ACCENT_AMBER; p.space_after = Pt(6)
    p = sctf.add_paragraph()
    p.text = "Proxmox REST API code, authentication headers, and UPID parsers are implemented and mock-tested, but real physical live migration over external hypervisors remains pending physical lab scheduling."
    p.font.size = Pt(9.5); p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 15: TESTING & VALIDATION
    # =========================================================================
    s15 = add_base_slide("14 // VERIFICATION & TESTING", "Comprehensive Automated Test Suite & Build Verification")

    # 3 Summary Metric Cards on Top
    metric_w = Inches(3.75)
    metric_h = Inches(1.3)

    m1 = add_card(s15, Inches(0.8), Inches(1.6), metric_w, metric_h, "BACKEND TEST SUITE")
    mtf1 = m1.text_frame; mtf1.margin_top = Inches(0.45); mtf1.margin_left = Inches(0.2); mtf1.word_wrap = True
    p = mtf1.paragraphs[0]; p.text = "96 Passed / 0 Failed"
    p.font.bold = True; p.font.size = Pt(18); p.font.color.rgb = ACCENT_EMERALD
    p2 = mtf1.add_paragraph(); p2.text = "Execution time: 19.47s across 11 test modules"
    p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_MUTED

    m2 = add_card(s15, Inches(4.79), Inches(1.6), metric_w, metric_h, "FRONTEND PRODUCTION BUILD")
    mtf2 = m2.text_frame; mtf2.margin_top = Inches(0.45); mtf2.margin_left = Inches(0.2); mtf2.word_wrap = True
    p = mtf2.paragraphs[0]; p.text = "1,891 Modules Transformed"
    p.font.bold = True; p.font.size = Pt(18); p.font.color.rgb = ACCENT_BLUE
    p2 = mtf2.add_paragraph(); p2.text = "0 TypeScript errors • Clean Vite/Tailwind bundle"
    p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_MUTED

    m3 = add_card(s15, Inches(8.78), Inches(1.6), metric_w, metric_h, "PPO EVALUATION SUITE")
    mtf3 = m3.text_frame; mtf3.margin_top = Inches(0.45); mtf3.margin_left = Inches(0.2); mtf3.word_wrap = True
    p = mtf3.paragraphs[0]; p.text = "600 Episodes Evaluated"
    p.font.bold = True; p.font.size = Pt(18); p.font.color.rgb = ACCENT_INDIGO
    p2 = mtf3.add_paragraph(); p2.text = "10 scenarios across Train, Val, and Unseen Test splits"
    p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_MUTED

    # Detailed Test Module Card below
    det_card = add_card(s15, Inches(0.8), Inches(3.05), Inches(11.733), Inches(3.75), "Detailed Test Verification Coverage")
    dttf = det_card.text_frame; dttf.margin_top = Inches(0.5); dttf.margin_left = Inches(0.3); dttf.word_wrap = True

    test_modules = [
        ("test_safety_gate.py (12 Scenarios)", "Verifies all 8 safety rules individually: blocks identical host, offline node, stopped VM, high RAM, high CPU, and cooldown violations."),
        ("test_migration_lifecycle.py (10 Scenarios)", "Verifies 12-state FSM progression (RECOMMENDED -> VERIFIED); asserts illegal state transitions raise InvalidStateTransitionError."),
        ("test_observation_spec.py (8 Scenarios)", "Verifies exact 103 float feature dimension, [-1.0, 1.0] mathematical bounds, and deterministic node/VM sorting orders."),
        ("test_provider_contracts.py (10 Scenarios)", "Verifies BaseVirtualizationProvider compliance for Simulation, Proxmox, and Libvirt; tests error isolation and disconnect truthfulness."),
        ("test_api_behavior.py & test_websocket.py", "Verifies FastAPI REST routing, secret masking in /config, operator key auth, and 2.0s WebSocket telemetry broadcasting.")
    ]
    for head, body in test_modules:
        p = dttf.add_paragraph(); p.text = f"• {head}:"; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = TEXT_PRIMARY
        p2 = dttf.add_paragraph(); p2.text = f"  {body}"; p2.font.size = Pt(9.5); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(4)

    # =========================================================================
    # SLIDE 16: CURRENT ACHIEVEMENTS
    # =========================================================================
    s16 = add_base_slide("15 // PROJECT ACHIEVEMENTS", "Verified Deliverables & Key Technical Contributions")

    # 4 Cards highlighting major technical achievements
    ach_w = Inches(5.7)
    ach_h = Inches(2.45)

    a1 = add_card(s16, Inches(0.8), Inches(1.6), ach_w, ach_h, "1. Safe Autonomous Infrastructure Decoupling")
    atf1 = a1.text_frame; atf1.margin_top = Inches(0.5); atf1.margin_left = Inches(0.25); atf1.word_wrap = True
    p = atf1.paragraphs[0]
    p.text = "Successfully engineered a multi-tier architecture where Deep RL is restricted to generating candidate proposals, while deterministic software gates unconditionally enforce physical hypervisor safety. Eliminates the risk of catastrophic RL hallucinations on production infrastructure."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    a2 = add_card(s16, Inches(6.833), Inches(1.6), ach_w, ach_h, "2. Resolution of Policy Collapse (PPO V5)")
    atf2 = a2.text_frame; atf2.margin_top = Inches(0.5); atf2.margin_left = Inches(0.25); atf2.word_wrap = True
    p = atf2.paragraphs[0]
    p.text = "Diagnosed and resolved critical covariate shift in PPO V4 (which collapsed to 100% No-Op due to single-scenario training). Engineered a 4-scenario balanced sampler resulting in +319.29 points overall improvement and +154.93 on unseen test benchmarks."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    a3 = add_card(s16, Inches(0.8), Inches(4.3), ach_w, ach_h, "3. Complete 12-State FSM with QEMU Guest Ping")
    atf3 = a3.text_frame; atf3.margin_top = Inches(0.5); atf3.margin_left = Inches(0.25); atf3.word_wrap = True
    p = atf3.paragraphs[0]
    p.text = "Implemented a stateful migration lifecycle that goes beyond 'fire-and-forget' API dispatch. Tasks are only marked completed after asserting residency on the destination node and querying QEMU guest-agent health over the hypervisor bus."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    a4 = add_card(s16, Inches(6.833), Inches(4.3), ach_w, ach_h, "4. Premium 3D WebGL Control Plane")
    atf4 = a4.text_frame; atf4.margin_top = Inches(0.5); atf4.margin_left = Inches(0.25); atf4.word_wrap = True
    p = atf4.paragraphs[0]
    p.text = "Built a responsive, production-ready React 19 control plane featuring a Three.js spatial cluster, Lenis smooth scrolling, live WebSocket telemetry, 103-dimensional schema inspection, and append-only forensic audit trails."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 17: HONEST LIMITATIONS & BOUNDARIES
    # =========================================================================
    s17 = add_base_slide("16 // LIMITATIONS & BOUNDARIES", "Honest Academic Boundaries: What is Implemented vs. Pending")

    lim_w = Inches(3.75)
    lim_h = Inches(5.2)

    # Col 1: Software / Simulation (Verified)
    l1 = add_card(s17, Inches(0.8), Inches(1.6), lim_w, lim_h, "1. Validated in Simulation", border_color=ACCENT_EMERALD)
    ltf1 = l1.text_frame; ltf1.margin_top = Inches(0.55); ltf1.margin_left = Inches(0.2); ltf1.word_wrap = True
    p = ltf1.paragraphs[0]; p.text = "COMPLETELY VERIFIED:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_EMERALD; p.space_after = Pt(6)
    p = ltf1.add_paragraph()
    p.text = "• 103-dim state vector math\n• PPO V5 inference engine\n• 8-rule deterministic safety gate\n• 12-state FSM transitions\n• 60-second cooldown lock\n• Multi-node load balancing\n• Emulated memory dirtying\n• 96 automated tests passing"
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    # Col 2: Code Implemented (Unverified on Hardware)
    l2 = add_card(s17, Inches(4.79), Inches(1.6), lim_w, lim_h, "2. Software Implemented (Hardware Unverified)", border_color=ACCENT_AMBER)
    ltf2 = l2.text_frame; ltf2.margin_top = Inches(0.55); ltf2.margin_left = Inches(0.2); ltf2.word_wrap = True
    p = ltf2.paragraphs[0]; p.text = "IMPLEMENTED BUT UNVERIFIED:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_AMBER; p.space_after = Pt(6)
    p = ltf2.add_paragraph()
    p.text = "• Proxmox VE 9.x REST client\n• Token header authentication\n• Real cluster node discovery\n• Real VM live migration dispatch\n• Real UPID task stream\n• Real QEMU guest-agent ping\n• Shared vs local storage checks\n• (Tested via unit mock tests)"
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    # Col 3: Current Boundaries & Future Needs
    l3 = add_card(s17, Inches(8.78), Inches(1.6), lim_w, lim_h, "3. Known Architectural Boundaries", border_color=ACCENT_RED)
    ltf3 = l3.text_frame; ltf3.margin_top = Inches(0.55); ltf3.margin_left = Inches(0.2); ltf3.word_wrap = True
    p = ltf3.paragraphs[0]; p.text = "HONEST LIMITATIONS:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_RED; p.space_after = Pt(6)
    p = ltf3.add_paragraph()
    p.text = "• Fixed Cluster Size: Discrete(7) designed for 3 nodes / 6 VMs; requires GNN for N-node clusters.\n• 2-Node Quorum Risk: 2-node lab cluster loses quorum on 1 node failure without external QDevice.\n• Libvirt Windows Friction: Libvirt C-bindings missing on Windows; stubbed in current code.\n• Lab Rack Pending: Physical hardware validation scheduled for college server lab."
    p.font.size = Pt(10); p.font.color.rgb = TEXT_SECONDARY

    # =========================================================================
    # SLIDE 18: FUTURE WORK & CONCLUSION
    # =========================================================================
    s18 = add_base_slide("17 // ROADMAP & CONCLUSION", "Future Roadmap & Project Conclusion")

    # Left Card: Future Roadmap
    c_fw = add_card(s18, Inches(0.8), Inches(1.6), Inches(6.8), Inches(5.2), "Future Development Roadmap")
    fwtf = c_fw.text_frame; fwtf.margin_top = Inches(0.55); fwtf.margin_left = Inches(0.3); fwtf.word_wrap = True

    roadmap_items = [
        ("1. Physical Laboratory Deployment", "Deploy VMotion AI against a dedicated 3-node physical server rack running Proxmox VE 9.2 in the VIT networking laboratory."),
        ("2. Corosync QDevice Integration", "Deploy an external Raspberry Pi or VM running corosync-qnetd to provide a 3rd vote for fault-tolerant 2-node cluster quorum."),
        ("3. Graph Neural Network (GNN) Policy", "Replace fixed 103-dim vector with a Graph Convolutional Network (GCN) to dynamically support variable-sized clusters with hundreds of hosts and VMs."),
        ("4. Predictive Workload Forecasting", "Integrate temporal forecasting (LSTM / PatchTST) to predict CPU spikes 5 minutes in advance, initiating live migration before contention occurs."),
        ("5. Lightweight KVM Agent Daemon", "Deploy a Python-based REST agent (vmotion-kvm-agent) directly on Linux hypervisors to eliminate Libvirt C-binding friction.")
    ]
    for head, body in roadmap_items:
        p = fwtf.add_paragraph(); p.text = head; p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = ACCENT_BLUE
        p2 = fwtf.add_paragraph(); p2.text = body; p2.font.size = Pt(9); p2.font.color.rgb = TEXT_SECONDARY; p2.space_after = Pt(4)

    # Right Card: Academic Conclusion
    c_con = add_card(s18, Inches(7.88), Inches(1.6), Inches(4.65), Inches(5.2), "Academic Conclusion", border_color=ACCENT_INDIGO)
    ctf = c_con.text_frame; ctf.margin_top = Inches(0.55); ctf.margin_left = Inches(0.25); ctf.word_wrap = True

    p = ctf.paragraphs[0]; p.text = "CORE TAKEAWAY:"
    p.font.bold = True; p.font.size = Pt(11); p.font.color.rgb = ACCENT_INDIGO; p.space_after = Pt(6)
    p = ctf.add_paragraph()
    p.text = "\"VMotion AI demonstrates that Deep Reinforcement Learning can solve non-linear multi-tenant cloud rebalancing without compromising hypervisor stability—provided the statistical AI is subordinated to a deterministic, fail-closed safety gate and human operator governance.\""
    p.font.size = Pt(11); p.font.italic = True; p.font.color.rgb = TEXT_PRIMARY; p.space_after = Pt(16)

    p = ctf.add_paragraph(); p.text = "KEY PROJECT METRICS:"
    p.font.bold = True; p.font.size = Pt(10); p.font.color.rgb = TEXT_PRIMARY; p.space_after = Pt(4)
    p = ctf.add_paragraph()
    p.text = "• Model: MaskablePPO V5 (SHA-256: bc47c2a5...)\n• Test Performance: +154.93 on unseen test scenarios\n• Safety Invariants: 8 deterministic rules (Fail-Closed)\n• FSM Lifecycle: 12 states with QEMU guest ping\n• Test Coverage: 96 passing backend unit/E2E tests\n• Software Completion: 91.5% | Hardware: 15.0%"
    p.font.size = Pt(10); p.font.bold = True; p.font.color.rgb = TEXT_SECONDARY

    # Save Presentation
    prs.save(OUTPUT_PPTX)
    print(f"Presentation generated successfully: {OUTPUT_PPTX}")

if __name__ == "__main__":
    create_presentation()
