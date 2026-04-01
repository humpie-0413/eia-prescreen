"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Shield,
  FileText,
  BarChart3,
  Map,
  Scale,
  Brain,
  Database,
  ArrowRight,
  Layers,
  Search,
  ClipboardCheck,
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] as const },
  }),
};

const FEATURES = [
  {
    icon: Shield,
    title: "입지 리스크 분석",
    desc: "64개 규칙 엔진이 16개 도메인에서 Critical/Major/Review/Info 4단계로 리스크를 식별합니다.",
    color: "text-red-500",
    bg: "bg-red-500/10",
  },
  {
    icon: Brain,
    title: "AI 초안 생성",
    desc: "103건 실제 평가서 원문(RAG)과 LLM을 결합하여 6장 18섹션 초안을 자동 생성합니다.",
    color: "text-teal-600",
    bg: "bg-teal-500/10",
  },
  {
    icon: BarChart3,
    title: "검토의견 예측",
    desc: "9,973건 과거 협의 데이터를 분석하여 예상 지적항목과 확률을 예측합니다.",
    color: "text-violet-500",
    bg: "bg-violet-500/10",
  },
  {
    icon: Scale,
    title: "규제 자동 매칭",
    desc: "175개 법령 매핑 테이블로 용도지역, 보호구역, EIA 임계값을 자동 매칭합니다.",
    color: "text-amber-600",
    bg: "bg-amber-500/10",
  },
  {
    icon: Search,
    title: "RAG 원문 검색",
    desc: "6,103개 청크에서 한국어 임베딩으로 실제 환경영향평가서 원문을 검색합니다.",
    color: "text-blue-500",
    bg: "bg-blue-500/10",
  },
  {
    icon: Map,
    title: "리스크 맵",
    desc: "MapLibre GL 기반 500m/1km 버퍼와 규제 레이어를 시각화합니다.",
    color: "text-green-600",
    bg: "bg-green-500/10",
  },
];

const STATS = [
  { value: "103건", label: "환경영향평가서 원문", sub: "16개 사업유형" },
  { value: "9,973건", label: "과거 협의 데이터", sub: "패턴 분석 기반" },
  { value: "64개", label: "리스크 규칙", sub: "16개 도메인" },
  { value: "175개", label: "규제 매핑", sub: "법령 자동 매칭" },
  { value: "84건", label: "유사사례", sub: "큐레이션 사례" },
  { value: "18개", label: "데이터 커넥터", sub: "공공 API 연동" },
];

const TECH_STACK = [
  { label: "Next.js 16", desc: "App Router + TypeScript" },
  { label: "FastAPI", desc: "Python 비동기 백엔드" },
  { label: "DeepSeek V3", desc: "AI 해석 + 초안 생성" },
  { label: "ChromaDB", desc: "벡터 RAG 검색" },
  { label: "MapLibre GL", desc: "오픈소스 지도" },
  { label: "PostgreSQL", desc: "PostGIS 공간 질의" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ─── Hero ─── */}
      <section className="relative overflow-hidden px-4 pt-20 pb-24 md:pt-32 md:pb-32">
        {/* Decorative orbs */}
        <div className="absolute top-20 -left-32 w-96 h-96 rounded-full bg-teal-400/10 blur-3xl animate-float pointer-events-none" />
        <div className="absolute bottom-10 -right-32 w-80 h-80 rounded-full bg-green-400/10 blur-3xl animate-float-slow pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-teal-500/10 text-teal-700 dark:text-teal-400 text-sm font-medium mb-6">
              <Layers className="size-4" />
              환경영향평가 사전검토 지원 도구
            </div>
          </motion.div>

          <motion.h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight tracking-tight"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            사업지 입력 한 번으로
            <br />
            <span className="text-teal-600 dark:text-teal-400">
              입지 리스크
            </span>
            를 파악합니다
          </motion.h1>

          <motion.p
            className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            공공 데이터, 사례 라이브러리, 실제 평가서 원문을 바탕으로 우선 검토 항목을 근거와 함께 제시합니다.
          </motion.p>

          <motion.div
            className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link
              href="/screening/new"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-teal-600 hover:bg-teal-700 text-white font-semibold text-base transition-all hover:shadow-lg hover:shadow-teal-500/20 active:scale-[0.98]"
            >
              스크리닝 시작
              <ArrowRight className="size-4" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full border border-border text-foreground font-medium text-sm hover:bg-accent transition-colors"
            >
              주요 기능 보기
            </a>
          </motion.div>
        </div>
      </section>

      {/* ─── Stats bar ─── */}
      <section className="border-y border-border bg-card/50">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 md:gap-8">
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                className="text-center"
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-50px" }}
                custom={i}
              >
                <p className="text-2xl md:text-3xl font-bold text-teal-600 dark:text-teal-400">
                  {stat.value}
                </p>
                <p className="text-sm font-medium mt-1">{stat.label}</p>
                <p className="text-xs text-muted-foreground">{stat.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section id="features" className="px-4 py-20 md:py-28">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="text-center mb-14"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl md:text-4xl font-bold">주요 기능</h2>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
              규칙 엔진, AI 해석, RAG 원문 검색을 결합하여 환경영향평가 사전검토의 전 과정을 지원합니다.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((feat, i) => (
              <motion.div
                key={feat.title}
                className="group relative rounded-2xl border border-border bg-card p-6 transition-all hover:shadow-lg hover:shadow-teal-500/5 hover:border-teal-500/30"
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-30px" }}
                custom={i}
              >
                <div
                  className={`inline-flex items-center justify-center size-11 rounded-xl ${feat.bg} ${feat.color} mb-4`}
                >
                  <feat.icon className="size-5" />
                </div>
                <h3 className="text-base font-semibold mb-2">{feat.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feat.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Workflow ─── */}
      <section className="px-4 py-20 bg-card/50 border-y border-border">
        <div className="max-w-5xl mx-auto">
          <motion.h2
            className="text-3xl md:text-4xl font-bold text-center mb-14"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            사전검토 흐름
          </motion.h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { step: "01", icon: ClipboardCheck, title: "사업 입력", desc: "위치와 사업유형을 입력합니다" },
              { step: "02", icon: Database, title: "데이터 수집", desc: "18개 공공 API에서 환경 데이터를 수집합니다" },
              { step: "03", icon: Shield, title: "리스크 분석", desc: "64개 규칙으로 입지 리스크를 식별합니다" },
              { step: "04", icon: FileText, title: "보고서 생성", desc: "PDF 보고서와 초안을 자동 생성합니다" },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                className="relative text-center"
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                custom={i}
              >
                <div className="inline-flex items-center justify-center size-14 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 mb-4">
                  <item.icon className="size-6" />
                </div>
                <div className="text-xs font-bold text-teal-600 dark:text-teal-400 mb-1">
                  STEP {item.step}
                </div>
                <h3 className="font-semibold mb-1">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Tech stack ─── */}
      <section className="px-4 py-20">
        <div className="max-w-4xl mx-auto">
          <motion.h2
            className="text-3xl md:text-4xl font-bold text-center mb-10"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            기술 스택
          </motion.h2>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {TECH_STACK.map((tech, i) => (
              <motion.div
                key={tech.label}
                className="rounded-xl border border-border bg-card p-4 text-center"
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                custom={i}
              >
                <p className="font-semibold text-sm">{tech.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {tech.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="px-4 py-20 bg-card/50 border-t border-border">
        <motion.div
          className="max-w-2xl mx-auto text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-2xl md:text-3xl font-bold">
            지금 사전검토를 시작하세요
          </h2>
          <p className="mt-3 text-muted-foreground">
            사업 위치와 유형만 입력하면, 입지 리스크와 규제 매칭 결과를 즉시 확인할 수 있습니다.
          </p>
          <Link
            href="/screening/new"
            className="inline-flex items-center gap-2 mt-8 px-8 py-3.5 rounded-full bg-teal-600 hover:bg-teal-700 text-white font-semibold transition-all hover:shadow-lg hover:shadow-teal-500/20 active:scale-[0.98]"
          >
            스크리닝 시작
            <ArrowRight className="size-4" />
          </Link>
        </motion.div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-border px-4 py-8">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="size-6 rounded-md bg-teal-600 flex items-center justify-center">
              <span className="text-white text-[10px] font-bold">E</span>
            </div>
            <span className="font-medium text-foreground">EIA Pre-Screen</span>
          </div>
          <p>
            이 도구는 법적 판정 시스템이 아닙니다. 전문가 현장조사와 법적 검토가 필요합니다.
          </p>
          <p>MIT License</p>
        </div>
      </footer>
    </div>
  );
}
