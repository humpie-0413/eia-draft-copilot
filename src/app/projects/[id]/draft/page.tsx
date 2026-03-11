"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import type { DraftScaffold, ScaffoldSection } from "@/types/section";
import { getDraftScaffold } from "@/lib/section-api";
import { ScaffoldSectionView } from "@/components/section/scaffold-section-view";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ListChecks } from "lucide-react";

export default function DraftScaffoldPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = params.id as string;
  const highlightSection = searchParams.get("section");

  const [scaffold, setScaffold] = useState<DraftScaffold | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(
    highlightSection,
  );

  // 섹션 ref (스크롤용)
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const fetchScaffold = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getDraftScaffold(projectId);
      setScaffold(result);
    } catch (err) {
      console.error("초안 뼈대 조회 실패:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchScaffold();
  }, [fetchScaffold]);

  // 하이라이트 섹션으로 스크롤
  useEffect(() => {
    if (highlightSection && sectionRefs.current[highlightSection]) {
      sectionRefs.current[highlightSection]?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [highlightSection, scaffold]);

  const handleNavClick = (key: string) => {
    setActiveSection(key);
    sectionRefs.current[key]?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  // 증거가 있는 섹션과 없는 섹션 분리
  const sectionsWithEvidence =
    scaffold?.sections.filter((s) => s.evidence_entries.length > 0) ?? [];
  const sectionsWithoutEvidence =
    scaffold?.sections.filter((s) => s.evidence_entries.length === 0) ?? [];

  return (
    <div className="flex gap-6">
      {/* 좌측 네비게이션 사이드바 */}
      <aside className="hidden w-56 shrink-0 lg:block">
        <div className="sticky top-6 space-y-1">
          <div className="mb-3 flex items-center gap-2">
            <Link href={`/projects/${projectId}/sections`}>
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <span className="text-sm font-medium">섹션 목차</span>
          </div>
          {scaffold?.sections.map((sec) => (
            <button
              key={sec.section_key}
              onClick={() => handleNavClick(sec.section_key)}
              className={`flex w-full items-center justify-between rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
                activeSection === sec.section_key
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <span>{sec.title}</span>
              {sec.evidence_entries.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-[10px] px-1.5">
                  {sec.evidence_entries.length}
                </Badge>
              )}
            </button>
          ))}
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <main className="min-w-0 flex-1 space-y-6">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={`/projects/${projectId}/sections`} className="lg:hidden">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h2 className="text-2xl font-bold tracking-tight">
                초안 뼈대
              </h2>
              <p className="text-sm text-muted-foreground">
                evidence 기반 근거 배치 — 총{" "}
                {scaffold?.total_evidence_count ?? 0}건의 근거 데이터
              </p>
            </div>
          </div>
          <Link href={`/projects/${projectId}/sections`}>
            <Button variant="outline">
              <ListChecks className="mr-2 h-4 w-4" />
              섹션 현황
            </Button>
          </Link>
        </div>

        {loading ? (
          <p className="py-16 text-center text-muted-foreground">
            초안 뼈대를 생성하는 중…
          </p>
        ) : (
          <>
            {/* 근거가 있는 섹션 */}
            {sectionsWithEvidence.map((sec) => (
              <div
                key={sec.section_key}
                ref={(el) => {
                  sectionRefs.current[sec.section_key] = el;
                }}
              >
                <ScaffoldSectionView section={sec} />
              </div>
            ))}

            {/* 근거 미수집 섹션 요약 */}
            {sectionsWithoutEvidence.length > 0 && (
              <div className="rounded-md border border-dashed p-4">
                <p className="mb-2 text-sm font-medium text-muted-foreground">
                  증거 미수집 섹션 ({sectionsWithoutEvidence.length}개)
                </p>
                <div className="flex flex-wrap gap-2">
                  {sectionsWithoutEvidence.map((sec) => (
                    <Badge
                      key={sec.section_key}
                      variant="outline"
                      className="text-xs text-muted-foreground"
                    >
                      {sec.title}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
