"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Film,
  Sparkles,
  Play,
  Building2,
  Brain,
  Route,
  Video,
  CheckCircle2,
  Camera,
  Zap,
  Sparkle,
  Compass,
  Check,
  X,
} from "lucide-react";

/* ── Interactive Pipeline Stage Definition ── */
const PIPELINE_STAGES = [
  {
    id: 1,
    phase: "Phase 01",
    title: "Ingestion & Image QA",
    tagline: "Cryptographic validation and quality scoring",
    icon: Building2,
    description:
      "Batch-upload property photographs. The system executes cryptographic SHA-256 deduplication, EXIF orientation correction, and computes sub-pixel sharpness, contrast, and illumination scores.",
    metrics: [
      { label: "Deduplication", value: "SHA-256 Bitwise" },
      { label: "Min Resolution", value: "512 × 512 px" },
      { label: "Quality Checks", value: "Sharpness & Lighting" },
    ],
    highlight: "Automated QA gates prevent degraded source inputs from entering video synthesis.",
  },
  {
    id: 2,
    phase: "Phase 02",
    title: "Gemini Scene Intelligence",
    tagline: "Multimodal room & spatial reasoning",
    icon: Brain,
    description:
      "Google Gemini 2.5 Flash inspects each photo, accurately categorizing spaces (Living Room, Master Suite, Gourmet Kitchen), detecting natural/artificial lighting fixtures, and identifying architectural doorways.",
    metrics: [
      { label: "Vision Model", value: "Gemini 2.5 Flash" },
      { label: "Room Taxonomy", value: "15+ Spatial Categories" },
      { label: "Doorway Mapping", value: "Adjacency Discovery" },
    ],
    highlight: "Deep understanding of visual geometry and architectural continuity.",
  },
  {
    id: 3,
    phase: "Phase 03",
    title: "Topological Route Planning",
    tagline: "Graph-ordered natural traversal & camera dolly scripting",
    icon: Route,
    description:
      "Constructs a connected scene graph to order rooms in human walkthrough sequence (Exterior ➔ Entrance ➔ Living ➔ Kitchen ➔ Suites). Scripts restrained, cinematic camera motions tailored to room acoustics and size.",
    metrics: [
      { label: "Graph Engine", value: "Topological Ordering" },
      { label: "Motions", value: "Push-In, Pan, Orbit, Pedestal" },
      { label: "Safety Bounds", value: "Bathroom/Tight Space Restraints" },
    ],
    highlight: "Eliminates jarring jump cuts and unnatural camera velocities.",
  },
  {
    id: 4,
    phase: "Phase 04",
    title: "Image-to-Video Rendering",
    tagline: "Pluggable cinematic motion engines",
    icon: Video,
    description:
      "Renders each planned scene into a stabilized HD clip. Choose a generative engine (Gemini Veo 3.1) for synthesized motion, or a plate-based engine — the JSON2Video cloud renderer, or the built-in local renderer — which moves a virtual camera over your original photograph so the property is reproduced exactly. Artifact checks ensure consistent frame rates and structural integrity.",
    metrics: [
      { label: "Engines", value: "Veo 3.1 · JSON2Video · Local" },
      { label: "Output Spec", value: "1080p HD @ 24fps" },
      { label: "Post-QA", value: "Bitrate & Artifact Filtering" },
    ],
    highlight: "Produces photorealistic video tours ready for luxury listing presentations.",
  },
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [activeStage, setActiveStage] = useState(1);
  const [isPlayingDemo, setIsPlayingDemo] = useState(false);
  const [activeRoomIndex, setActiveRoomIndex] = useState(0);

  const rooms = [
    { name: "Modern Exterior", type: "Exterior", motion: "Slow Forward Dolly", icon: "🏡" },
    { name: "Grand Foyer", type: "Entrance", motion: "Smooth Push-In", icon: "🚪" },
    { name: "Open Living Salon", type: "Living Room", motion: "Gentle Left-to-Right Pan", icon: "🛋️" },
    { name: "Chef's Kitchen", type: "Kitchen", motion: "Low Orbit Around Island", icon: "🍳" },
    { name: "Primary Master Suite", type: "Bedroom", motion: "Pedestal Up Reveal", icon: "🛏️" },
  ];

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // Demo playback loop
  useEffect(() => {
    if (!isPlayingDemo) return;
    const interval = setInterval(() => {
      setActiveRoomIndex((prev) => (prev + 1) % rooms.length);
    }, 2800);
    return () => clearInterval(interval);
  }, [isPlayingDemo, rooms.length]);

  const currentStageData = PIPELINE_STAGES.find((s) => s.id === activeStage) || PIPELINE_STAGES[0];

  return (
    <div className="relative min-h-screen bg-[var(--bg-0)] text-[var(--text-1)]">
      {/* ── STICKY TOP NAVBAR — Deep navy, distinct from ivory content ── */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-400"
        style={{
          background: scrolled ? "rgba(13,18,32,0.97)" : "rgba(13,18,32,0.92)",
          backdropFilter: "blur(24px) saturate(180%)",
          WebkitBackdropFilter: "blur(24px) saturate(180%)",
          borderBottom: "1px solid rgba(184,136,43,0.15)",
          boxShadow: scrolled ? "0 8px 32px rgba(0,0,0,0.25)" : "none",
        }}
      >
        {/* Gold accent underline */}
        <div
          className="h-[2px] w-full"
          style={{ background: "linear-gradient(90deg, transparent 0%, rgba(184,136,43,0.8) 30%, #d4a843 50%, rgba(184,136,43,0.8) 70%, transparent 100%)" }}
        />
        <div className="max-w-7xl mx-auto px-6 sm:px-10 h-16 flex items-center justify-between">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-3 group">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-300"
              style={{ background: "linear-gradient(135deg, #d4a843 0%, #a0711a 100%)", boxShadow: "0 4px 16px rgba(184,136,43,0.35)" }}
            >
              <Film size={19} className="text-[#0d1220]" />
            </div>
            <div>
              <span className="font-display text-lg font-bold text-white tracking-tight">
                Ciné<span style={{ color: "#d4a843" }}>Estate</span>
              </span>
              <span className="hidden sm:block text-[9px] uppercase font-bold tracking-[0.2em]" style={{ color: "rgba(212,168,67,0.65)" }}>
                AI Studio
              </span>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-8">
            {[
              { href: "#pipeline", label: "Pipeline" },
              { href: "#simulator", label: "Preview" },
              { href: "#comparison", label: "Why CinéEstate" },
              { href: "#specifications", label: "Architecture" },
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-xs uppercase tracking-wider font-semibold transition-all duration-200 hover:opacity-100"
                style={{ color: "rgba(241,245,249,0.60)", transition: "color 0.2s ease" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#d4a843")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(241,245,249,0.60)")}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div className="flex items-center gap-3">
            <Link
              href="/studio"
              className="btn-gold px-5 py-2.5 rounded-xl text-xs font-bold inline-flex items-center gap-2"
            >
              <span>Launch Studio</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO SECTION ── */}
      <section className="relative pt-44 pb-28 px-6 sm:px-8 overflow-hidden hero-spotlight">
        <div className="absolute inset-0 hero-grid opacity-50 pointer-events-none" />
        {/* Extra ambient glow orbs */}
        <div className="absolute top-32 left-1/4 w-96 h-96 rounded-full pointer-events-none" style={{ background: "radial-gradient(circle, rgba(184,136,43,0.06) 0%, transparent 70%)" }} />
        <div className="absolute bottom-0 right-1/4 w-72 h-72 rounded-full pointer-events-none" style={{ background: "radial-gradient(circle, rgba(13,18,32,0.04) 0%, transparent 70%)" }} />

        <div className="relative z-10 max-w-5xl mx-auto text-center space-y-10">
          {/* Floating eyebrow badge */}
          <div className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full border border-[var(--border-2)] bg-white/70 shadow-md anim-float" style={{ backdropFilter: "blur(12px)" }}>
            <Sparkles size={14} className="text-[var(--gold-2)]" />
            <span className="text-[11px] font-bold tracking-widest uppercase" style={{ color: "#8a6211" }}>
              Gemini 2.5 Flash · Pluggable Video Engines · AI-Powered Cinematography
            </span>
          </div>

          {/* Headline — larger, bolder */}
          <div className="space-y-3">
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.08] tracking-tight text-[var(--text-1)]">
              Turn Listing Photos Into
            </h1>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.08] tracking-tight anim-shimmer">
              Cinematic Video Tours
            </h1>
          </div>

          {/* Subheading */}
          <p className="text-base sm:text-lg md:text-xl text-[var(--text-2)] max-w-2xl mx-auto leading-relaxed" style={{ fontWeight: 400 }}>
            Upload your property photographs. Our AI pipeline understands room geometry, plans the optimal
            walkthrough sequence, and synthesizes stabilized HD video with restrained camera motion.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-2">
            <Link
              href="/studio"
              className="btn-gold px-10 py-4 rounded-2xl text-sm font-bold inline-flex items-center justify-center gap-3 glow-gold-lg w-full sm:w-auto shadow-xl"
            >
              <Play size={18} className="fill-current" />
              Launch Generation Studio
              <ArrowRight size={16} />
            </Link>
            <a
              href="#pipeline"
              className="btn-ghost px-8 py-4 rounded-2xl text-sm font-semibold inline-flex items-center justify-center gap-2 w-full sm:w-auto"
            >
              <span>Explore the Pipeline</span>
              <ArrowRight size={15} />
            </a>
          </div>

          {/* Key Metrics Bar */}
          <div className="pt-14 grid grid-cols-2 sm:grid-cols-4 gap-5 max-w-3xl mx-auto text-center" style={{ borderTop: "1px solid var(--border-1)" }}>
            {[
              { value: "4 Phases", label: "Autonomous Engine" },
              { value: "Gemini 2.5", label: "Scene Intelligence" },
              { value: "3 Engines", label: "Swappable Renderers" },
              { value: "< 90s", label: "Generation Speed" },
            ].map((m) => (
              <div key={m.label} className="p-6 rounded-2xl bg-white/80 border border-[var(--border-1)] shadow-md card-hover" style={{ backdropFilter: "blur(8px)" }}>
                <p className="font-display text-2xl sm:text-3xl font-bold" style={{ color: "var(--gold-2)" }}>{m.value}</p>
                <p className="text-[10px] uppercase font-bold tracking-wider mt-2" style={{ color: "var(--text-3)" }}>{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── INTERACTIVE SIMULATOR SHOWCASE ── */}
      <section id="simulator" className="py-24 px-6 sm:px-8">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <p className="text-xs font-bold tracking-[0.2em] uppercase text-[var(--gold-1)]">
              Interactive Preview
            </p>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-[var(--text-1)]">
              Topological Route &amp; Camera HUD
            </h2>
            <p className="text-sm text-[var(--text-2)] leading-relaxed">
              Experience how CinéEstate transforms disjointed still photos into a synchronized multi-scene camera journey.
            </p>
          </div>

          <div className="glass-gold rounded-3xl p-6 sm:p-10 border border-[var(--border-2)] shadow-2xl space-y-8">
            {/* Top HUD Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border-1)]">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-[var(--gold-dim)] border border-[var(--border-2)] flex items-center justify-center text-2xl shadow-inner">
                  {rooms[activeRoomIndex].icon}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-[var(--gold-1)] uppercase tracking-wider">
                      Shot 0{activeRoomIndex + 1} of 0{rooms.length}
                    </span>
                    <span className="badge badge-success text-[10px] font-mono">Stabilized Motion</span>
                  </div>
                  <h3 className="font-display text-xl font-bold text-[var(--text-1)]">
                    {rooms[activeRoomIndex].name}
                  </h3>
                </div>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={() => setIsPlayingDemo(!isPlayingDemo)}
                  className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all w-full sm:w-auto ${
                    isPlayingDemo
                      ? "bg-[var(--gold-1)] text-[#080a0d] shadow-lg shadow-[var(--gold-glow)]"
                      : "border border-[var(--border-2)] bg-[var(--gold-dim)] text-[var(--gold-2)] hover:bg-[var(--gold-glow)]"
                  }`}
                >
                  <Play size={14} className={isPlayingDemo ? "fill-current" : ""} />
                  {isPlayingDemo ? "Simulating Route…" : "Play Live Simulation"}
                </button>

                <Link
                  href="/studio"
                  className="btn-gold px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shrink-0"
                >
                  <span>Build Yours</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* Main Stage Display */}
            <div className="grid lg:grid-cols-12 gap-8 items-stretch">
              {/* Left 7 Cols: Video Simulation Canvas */}
              <div className="lg:col-span-7 relative rounded-3xl overflow-hidden bg-[#0a0f1d] border border-[var(--border-2)] min-h-[380px] flex flex-col justify-between p-6 sm:p-8 shadow-2xl">
                {/* Ambient glow in canvas */}
                <div className="absolute inset-0 bg-gradient-to-tr from-[#d4a853]/15 via-transparent to-transparent pointer-events-none" />

                {/* Top overlay metadata */}
                <div className="relative z-10 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 bg-[#0d1220]/90 px-3.5 py-1.5 rounded-full border border-white/10 text-xs font-mono text-[var(--gold-2)] shadow-md">
                    <Camera size={13} className="text-[var(--gold-1)]" />
                    <span>{rooms[activeRoomIndex].motion}</span>
                  </div>
                  <div className="flex items-center gap-2 bg-[#0d1220]/90 px-3.5 py-1.5 rounded-full border border-white/10 text-xs font-mono text-emerald-400 shadow-md">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    <span>1080p HD Ready</span>
                  </div>
                </div>

                {/* Center visual emblem */}
                <div className="relative z-10 text-center space-y-3 my-auto py-8">
                  <div className="w-20 h-20 rounded-3xl bg-amber-500/10 border border-amber-500/30 mx-auto flex items-center justify-center text-4xl shadow-xl shadow-[var(--gold-glow)]">
                    {rooms[activeRoomIndex].icon}
                  </div>
                  <p className="font-display text-2xl font-bold text-white">
                    {rooms[activeRoomIndex].name}
                  </p>
                  <p className="text-xs text-[var(--gold-2)] font-mono">
                    Scene Type: {rooms[activeRoomIndex].type}
                  </p>
                </div>

                {/* Bottom Scrubbing Timeline */}
                <div className="relative z-10 space-y-2.5 pt-4 border-t border-white/10">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                    <span>Scene 0{activeRoomIndex + 1} / 0{rooms.length}</span>
                    <span>1080p @ 24fps · Straight Cut Transition</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-2)] transition-all duration-500 rounded-full"
                      style={{ width: `${((activeRoomIndex + 1) / rooms.length) * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Right 5 Cols: Scene Sequence Graph */}
              <div className="lg:col-span-5 flex flex-col justify-between space-y-3">
                <p className="text-xs font-bold tracking-wider uppercase text-[var(--gold-1)] flex items-center gap-2 mb-2">
                  <Compass size={15} />
                  Topological Traversal Order
                </p>

                <div className="space-y-2.5 flex-1 flex flex-col justify-between">
                  {rooms.map((room, idx) => {
                    const isCurrent = idx === activeRoomIndex;
                    return (
                      <div
                        key={room.name}
                        onClick={() => setActiveRoomIndex(idx)}
                        className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                          isCurrent
                            ? "bg-[var(--gold-dim)] border-[var(--gold-1)] shadow-lg shadow-[var(--gold-glow)]"
                            : "bg-[var(--bg-card)] border-[var(--border-1)] hover:border-[var(--border-2)]"
                        }`}
                      >
                        <div className="flex items-center gap-3.5">
                          <span
                            className={`w-7 h-7 rounded-xl text-xs font-mono font-bold flex items-center justify-center ${
                              isCurrent
                                ? "bg-[var(--gold-1)] text-[#080a0d] shadow-md"
                                : "bg-[var(--bg-0)] text-[var(--text-3)] border border-[var(--border-1)]"
                            }`}
                          >
                            0{idx + 1}
                          </span>
                          <div>
                            <p
                              className={`text-xs sm:text-sm font-bold ${
                                isCurrent ? "text-[var(--text-1)]" : "text-[var(--text-2)]"
                              }`}
                            >
                              {room.name}
                            </p>
                            <p className="text-[11px] text-[var(--text-3)] font-mono mt-0.5">{room.motion}</p>
                          </div>
                        </div>

                        <span className="text-xl">{room.icon}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4-PHASE AUTONOMOUS PIPELINE ── */}
      <section id="pipeline" className="py-28 px-6 sm:px-8 border-y border-[var(--border-0)]" style={{ background: "linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%)" }}>
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <p className="text-xs font-bold tracking-[0.2em] uppercase text-[var(--gold-1)]">
              End-to-End Pipeline
            </p>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-[var(--text-1)]">
              Four Stages from Photo to Video
            </h2>
            <p className="text-sm text-[var(--text-2)] leading-relaxed">
              Every photograph traverses four specialized processing layers to ensure photorealism and spatial integrity.
            </p>
          </div>

          {/* Tab buttons */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {PIPELINE_STAGES.map((stg) => {
              const active = stg.id === activeStage;
              const Icon = stg.icon;
              return (
                <button
                  key={stg.id}
                  type="button"
                  onClick={() => setActiveStage(stg.id)}
                  className={`p-5 rounded-2xl border text-left transition-all ${
                    active
                      ? "bg-[var(--gold-dim)] border-[var(--gold-1)] shadow-xl shadow-[var(--gold-glow)]"
                      : "bg-[var(--bg-card)] border-[var(--border-1)] hover:border-[var(--border-2)] opacity-75 hover:opacity-100"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--gold-2)] font-mono">
                      {stg.phase}
                    </span>
                    <Icon size={18} className={active ? "text-[var(--gold-1)]" : "text-[var(--text-3)]"} />
                  </div>
                  <p className="text-sm font-bold text-[var(--text-1)] leading-snug">{stg.title}</p>
                </button>
              );
            })}
          </div>

          {/* Active Stage Detail Showcase */}
          <div className="glass-gold rounded-3xl p-8 sm:p-12 border border-[var(--border-2)] grid md:grid-cols-12 gap-10 items-center shadow-2xl">
            <div className="md:col-span-7 space-y-6">
              <div className="flex items-center gap-3">
                <span className="badge badge-gold font-mono">{currentStageData.phase}</span>
                <span className="text-xs font-mono text-[var(--text-3)]">Autonomous Execution</span>
              </div>

              <div className="space-y-2">
                <h3 className="font-display text-2xl sm:text-3xl font-bold text-[var(--text-1)]">
                  {currentStageData.title}
                </h3>
                <p className="text-xs font-semibold text-[var(--gold-2)] uppercase tracking-wider">
                  {currentStageData.tagline}
                </p>
              </div>

              <p className="text-sm text-[var(--text-2)] leading-relaxed">
                {currentStageData.description}
              </p>

              <div className="p-5 rounded-2xl bg-[var(--bg-0)] border border-[var(--border-1)] flex items-start gap-3.5 shadow-inner">
                <Sparkle size={18} className="text-[var(--gold-1)] shrink-0 mt-0.5" />
                <p className="text-xs text-[var(--text-2)] italic leading-relaxed">
                  {currentStageData.highlight}
                </p>
              </div>
            </div>

            <div className="md:col-span-5 space-y-5">
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--text-3)]">
                Stage Specifications
              </p>
              <div className="space-y-3">
                {currentStageData.metrics.map((m) => (
                  <div
                    key={m.label}
                    className="p-4 rounded-xl bg-[var(--bg-0)] border border-[var(--border-1)] flex items-center justify-between"
                  >
                    <span className="text-xs text-[var(--text-2)] font-medium">{m.label}</span>
                    <span className="text-xs font-mono font-bold text-[var(--gold-2)]">{m.value}</span>
                  </div>
                ))}
              </div>

              <div className="pt-3">
                <Link
                  href="/studio"
                  className="btn-gold w-full py-3.5 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-2 shadow-lg hover:scale-105"
                >
                  <span>Open Stage in Studio</span>
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── VALUE COMPARISON: WHY CINÉESTATE ── */}
      <section id="comparison" className="py-28 px-6 sm:px-8">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <p className="text-xs font-bold tracking-[0.2em] uppercase text-[var(--gold-1)]">
              The Strategic Advantage
            </p>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-[var(--text-1)]">
              Traditional Production vs. CinéEstate
            </h2>
            <p className="text-sm text-[var(--text-2)] leading-relaxed">
              Eliminate expensive on-site videography crews and multi-day turnarounds.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 items-stretch">
            {/* Traditional Card */}
            <div className="rounded-3xl p-8 sm:p-10 bg-[var(--bg-card)] border border-[var(--border-0)] space-y-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-display text-xl font-bold text-[var(--text-2)]">
                    Traditional Production
                  </h3>
                  <span className="badge badge-error">Legacy</span>
                </div>
                <ul className="space-y-4 text-xs sm:text-sm text-[var(--text-3)]">
                  <li className="flex items-start gap-3">
                    <X size={16} className="text-red-400 shrink-0 mt-0.5" />
                    <span>Cost ranges from $800 to $2,500 per property listing</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <X size={16} className="text-red-400 shrink-0 mt-0.5" />
                    <span>Requires 3–5 business days for shooting and manual editing</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <X size={16} className="text-red-400 shrink-0 mt-0.5" />
                    <span>Vulnerable to bad weather, dim daylight, and tenant scheduling</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <X size={16} className="text-red-400 shrink-0 mt-0.5" />
                    <span>Re-shoots require costly on-site return appointments</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* CinéEstate Card */}
            <div className="rounded-3xl p-8 sm:p-10 glass-gold border border-[var(--border-2)] space-y-6 flex flex-col justify-between shadow-2xl relative">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-display text-xl font-bold text-[var(--gold-2)]">
                    CinéEstate AI Studio
                  </h3>
                  <span className="badge badge-gold">Next-Gen</span>
                </div>
                <ul className="space-y-4 text-xs sm:text-sm text-[var(--text-1)]">
                  <li className="flex items-start gap-3">
                    <Check size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                    <span>Leverages existing MLS &amp; portfolio photographs instantly</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                    <span>Complete video walkthrough synthesized in under 90 seconds</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                    <span>AI lighting normalization &amp; steady-cam motion paths</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Check size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                    <span>Instant per-clip camera retries &amp; custom motion overrides</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── TECHNICAL SPECIFICATIONS ── */}
      <section id="specifications" className="py-28 px-6 sm:px-8 border-t border-[var(--border-0)]" style={{ background: "linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%)" }}>
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <p className="text-xs font-bold tracking-[0.2em] uppercase text-[var(--gold-1)]">
              Architecture &amp; Foundation
            </p>
            <h2 className="font-display text-3xl font-bold text-[var(--text-1)]">
              Built on Modern AI Primitives
            </h2>
          </div>

          <div className="grid sm:grid-cols-3 gap-6">
            <div className="p-8 rounded-3xl bg-[var(--bg-card)] border border-[var(--border-1)] space-y-4 shadow-md">
              <div className="w-12 h-12 rounded-2xl bg-[var(--gold-dim)] border border-[var(--border-2)] flex items-center justify-center shadow-inner">
                <Brain size={22} className="text-[var(--gold-2)]" />
              </div>
              <h4 className="font-bold text-base text-[var(--text-1)]">Gemini 2.5 Flash</h4>
              <p className="text-xs sm:text-sm text-[var(--text-2)] leading-relaxed">
                Multimodal spatial vision extracting architectural room categories, lighting conditions, and topological adjacency graphs.
              </p>
            </div>

            <div className="p-8 rounded-3xl bg-[var(--bg-card)] border border-[var(--border-1)] space-y-4 shadow-md">
              <div className="w-12 h-12 rounded-2xl bg-[var(--gold-dim)] border border-[var(--border-2)] flex items-center justify-center shadow-inner">
                <Video size={22} className="text-[var(--gold-2)]" />
              </div>
              <h4 className="font-bold text-base text-[var(--text-1)]">Pluggable Video Engines</h4>
              <p className="text-xs sm:text-sm text-[var(--text-2)] leading-relaxed">
                Google Veo 3.1 for generative image-to-video, plus plate-based renderers that
                move a camera over your original photographs. Plate-based motion is pixel-exact,
                so local fallback renders stay grounded in the source photograph — and a quota-limited engine degrades
                to the local renderer instead of failing the walkthrough.
              </p>
            </div>

            <div className="p-8 rounded-3xl bg-[var(--bg-card)] border border-[var(--border-1)] space-y-4 shadow-md">
              <div className="w-12 h-12 rounded-2xl bg-[var(--gold-dim)] border border-[var(--border-2)] flex items-center justify-center shadow-inner">
                <Zap size={22} className="text-[var(--gold-2)]" />
              </div>
              <h4 className="font-bold text-base text-[var(--text-1)]">FastAPI + Next.js</h4>
              <p className="text-xs sm:text-sm text-[var(--text-2)] leading-relaxed">
                Asynchronous task queue backend with real-time SSE progress streaming and modular client-side state machine.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CALL TO ACTION BANNER ── */}
      <section className="py-32 px-6 sm:px-8 border-t border-[var(--border-1)] text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 80% 60% at 50% 100%, rgba(184,136,43,0.06) 0%, transparent 70%)" }} />
        <div className="relative z-10 max-w-3xl mx-auto space-y-8">
          <p className="text-xs font-bold tracking-[0.2em] uppercase" style={{ color: "var(--gold-1)" }}>Get Started Today</p>
          <h2 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-[var(--text-1)] leading-tight">
            Ready for your first{" "}
            <span className="text-gold">cinematic walkthrough?</span>
          </h2>
          <p className="text-base sm:text-lg text-[var(--text-2)] max-w-xl mx-auto leading-relaxed">
            Upload property images and watch your listing transform into a professional video tour in minutes — no filming crew required.
          </p>
          <div className="pt-4">
            <Link
              href="/studio"
              className="btn-gold px-12 py-5 rounded-2xl text-sm font-bold inline-flex items-center gap-3 glow-gold-lg shadow-2xl"
            >
              <Play size={18} className="fill-current" />
              Launch Generation Studio
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ background: "var(--nav-bg)", borderTop: "1px solid rgba(184,136,43,0.15)" }} className="py-12 px-6 sm:px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #d4a843 0%, #a0711a 100%)" }}
            >
              <Film size={16} className="text-[#0d1220]" />
            </div>
            <span className="font-display font-bold text-base text-white">
              Ciné<span style={{ color: "#d4a843" }}>Estate</span>
            </span>
          </div>

          <p className="text-xs text-center" style={{ color: "rgba(148,163,184,0.7)" }}>
            AI-Powered Real Estate Walkthrough Video Generation · Gemini 2.5 · Swappable Video Engines
          </p>

          <div className="flex items-center gap-2 text-xs font-mono" style={{ color: "#4ade80" }}>
            <CheckCircle2 size={13} />
            <span>Systems Online</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
