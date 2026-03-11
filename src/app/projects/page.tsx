"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Project } from "@/types/project";
import type { PaginatedList } from "@/types/api";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, FlaskConical, GitCompareArrows, ListChecks } from "lucide-react";

const STATUS_LABELS: Record<string, string> = {
  draft: "초안",
  in_progress: "진행 중",
  review: "검토",
  completed: "완료",
  archived: "보관",
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<PaginatedList<Project>>("/api/v1/projects?limit=50")
      .then((res) => setProjects(res.items))
      .catch((err) => console.error("프로젝트 목록 조회 실패:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">프로젝트 목록</h2>
          <p className="text-sm text-muted-foreground">
            프로젝트를 선택하여 증거 작업대로 이동하세요.
          </p>
        </div>
      </div>

      {loading ? (
        <p className="py-16 text-center text-muted-foreground">
          불러오는 중…
        </p>
      ) : projects.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">
          등록된 프로젝트가 없습니다. 백엔드 API를 통해 프로젝트를 먼저 생성하세요.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Card key={project.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base">{project.name}</CardTitle>
                  <Badge variant="outline" className="text-xs">
                    {STATUS_LABELS[project.status] ?? project.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {project.description && (
                  <p className="mb-3 text-sm text-muted-foreground line-clamp-2">
                    {project.description}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Link href={`/projects/${project.id}/evidences`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      <FlaskConical className="mr-2 h-4 w-4" />
                      증거 작업대
                    </Button>
                  </Link>
                  <Link href={`/projects/${project.id}/similar-cases`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      <GitCompareArrows className="mr-2 h-4 w-4" />
                      유사사례
                    </Button>
                  </Link>
                  <Link href={`/projects/${project.id}/sections`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full">
                      <ListChecks className="mr-2 h-4 w-4" />
                      섹션 플래너
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
