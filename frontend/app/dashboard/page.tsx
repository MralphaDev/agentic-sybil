"use client";

import { useState } from "react";
import DashboardBackground from "@/components/dashboard/dashboard-background";
import DashboardHeader from "@/components/dashboard/dashboard-header";
import DashboardHeading from "@/components/dashboard/dashboard-heading";
import DashboardStatus from "@/components/dashboard/dashboard-status";
import DashboardStatCards from "@/components/dashboard/dashboard-stat-cards";
import AgentActivityPanel from "@/components/dashboard/agent-activity-panel";
import InvestigationResultsPanel from "@/components/dashboard/investigation-results-panel";
import DashboardFooter from "@/components/dashboard/dashboard-footer";
import { useInvestigationDashboard } from "@/components/dashboard/use-investigation-dashboard";
import InvestigationProgress, {
  type PipelineStage,
} from "@/components/investigation-progress";

export default function DashboardPage() {
  const dashboard = useInvestigationDashboard();
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#080809] text-zinc-100">
      <DashboardBackground />

      <div className="relative z-10 mx-auto max-w-[1800px] px-4 pb-8 sm:px-6 lg:px-10">
        <DashboardHeader
          status={dashboard.status}
          isCompleted={dashboard.isCompleted}
          isFailed={dashboard.isFailed}
        />

        <DashboardHeading
          runId={dashboard.runId}
          isCompleted={dashboard.isCompleted}
          isFailed={dashboard.isFailed}
        />

        <DashboardStatus message={dashboard.streamError} />

        <DashboardStatCards
          runId={dashboard.runId}
          eventCount={dashboard.events.length}
          resultAvailable={dashboard.result !== null}
          resultStatus={dashboard.resultStatus}
        />

        <section className="grid min-w-0 grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
          <AgentActivityPanel
            events={dashboard.events}
            isCompleted={dashboard.isCompleted}
            isFailed={dashboard.isFailed}
          />

          <InvestigationResultsPanel
            result={dashboard.result || null}
            resultStatus={dashboard.resultStatus}
            pipelineStages={pipelineStages}
            isFailed={dashboard.isFailed}
          />

          {dashboard.result === null && (
            <InvestigationProgress
              stages={pipelineStages}
              backendStatus={dashboard.resultStatus}
              failed={dashboard.isFailed}
            />
          )}
        </section>

        <DashboardFooter />
      </div>
    </main>
  );
}