"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search } from "lucide-react";
import { queryRag } from "@/lib/api";
import type { RagResponse } from "@/lib/api";

export default function RagPage() {

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RagResponse | null>(null);

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    try {
      const res = await queryRag(trimmed);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "검색 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isEmpty = query.trim().length === 0;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Search className="size-6" />
          환경영향평가서 원문 검색
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          RAG 기반으로 실제 환경영향평가서 원문에서 답변을 검색합니다.
        </p>
      </div>

      {/* Query input */}
      <div className="flex gap-2">
        <input
          data-testid="rag-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="예: 도로 사업의 비산먼지 저감방안은?"
          className="flex-1 rounded-lg border border-input bg-background px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <Button
          data-testid="rag-submit"
          onClick={handleSubmit}
          disabled={isEmpty || loading}
        >
          검색
        </Button>
      </div>
      {isEmpty && query.length > 0 && (
        <p className="text-xs text-muted-foreground">질문을 입력하세요</p>
      )}

      {/* Loading */}
      {loading && (
        <div data-testid="rag-loading" className="flex items-center gap-3 py-8 justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-primary" />
          <span className="text-sm text-muted-foreground">원문을 검색하고 있습니다...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Response */}
      {result && !loading && (
        <div className="space-y-4">
          {/* AI Answer */}
          <Card data-testid="rag-response">
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base">AI 답변</CardTitle>
                <Badge
                  variant="outline"
                  className="border-0 bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs"
                >
                  RAG 기반
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed whitespace-pre-line">
                {result.answer}
              </p>
            </CardContent>
          </Card>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold mb-3">
                참조 원문 ({result.sources.length}건)
              </h2>
              <div className="space-y-2">
                {result.sources.map((source, idx) => (
                  <Card key={idx} data-testid="rag-source">
                    <CardContent className="py-3 px-4 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">
                          {source.project_name}
                        </span>
                        <Badge variant="outline" className="text-xs border-0 bg-muted">
                          {source.year}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {source.chapter}장 {source.section}절
                        </span>
                        {source.page_range && (
                          <span className="text-xs text-muted-foreground">
                            p.{source.page_range}
                          </span>
                        )}
                        <span className="ml-auto text-xs font-medium text-teal-700 dark:text-teal-400">
                          {Math.round(source.similarity * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {source.excerpt}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <p className="text-xs text-muted-foreground text-center">
            {result.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
