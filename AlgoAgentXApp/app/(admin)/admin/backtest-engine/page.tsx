"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Code2, Save } from "lucide-react";
import { toast } from "sonner";

import { adminApi, type AdminBacktestEngineSource } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

export default function AdminBacktestEnginePage() {
  const [data, setData] = useState<AdminBacktestEngineSource | null>(null);
  const [sourceCode, setSourceCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.getAdminBacktestEngineSource();
      setData(response);
      setSourceCode(response.source_code || "");
    } catch (error: any) {
      toast.error(error?.message || "Failed to load backtest engine workspace");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    if (!window.confirm("Save updated backtest engine source code?")) return;
    setSaving(true);
    try {
      await adminApi.updateAdminBacktestEngineSource(sourceCode);
      toast.success("Backtest engine updated successfully");
      await load();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update backtest engine");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtest Engine Workspace"
        subtitle="Maintain the shared trading engine logic that handles entry, exit, stop loss, target, and execution rules for all strategies."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" className="rounded-xl" asChild>
              <Link href="/admin/backtests"><ArrowLeft className="mr-2 h-4 w-4" />Back to Admin Backtests</Link>
            </Button>
            <Button onClick={() => void save()} disabled={saving} className="rounded-xl bg-primary text-primary-foreground">
              <Save className="mr-2 h-4 w-4" />{saving ? "Saving..." : "Save Engine"}
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Code2 className="h-5 w-5" />engine/backtest_engine.py</CardTitle>
            <CardDescription>Edit the shared execution engine. Strategies should mainly generate buy/sell signals; this engine manages execution behavior.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <div className="h-96 animate-pulse rounded-xl bg-card/20" /> : (
              <textarea className={`${fieldClass} min-h-[720px] font-mono text-xs`} value={sourceCode} onChange={(e) => setSourceCode(e.target.value)} spellCheck={false} />
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle>Workflow Guidance</CardTitle>
              <CardDescription>Recommended admin workflow.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>1. Update the shared engine code here for execution-level rules.</p>
              <p>2. Keep strategy source code focused on generating long/short/flat signals.</p>
              <p>3. Use Strategy Workspace to verify code and run sandbox backtests.</p>
              <p>4. Publish only after validation and sandbox results pass.</p>
            </CardContent>
          </Card>

          <Card className="rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl">
            <CardHeader>
              <CardTitle>Supporting Files</CardTitle>
              <CardDescription>Read-only helpers used by the engine.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(data?.supporting_files || []).map((file) => (
                <div key={file.path} className="space-y-2">
                  <p className="text-sm font-medium text-foreground">{file.path}</p>
                  <textarea className={`${fieldClass} min-h-[220px] font-mono text-xs`} value={file.content} readOnly spellCheck={false} />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
