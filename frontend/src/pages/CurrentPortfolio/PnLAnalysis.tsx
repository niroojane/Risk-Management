import { useMutation } from '@tanstack/react-query';
import { FrameChart } from '@/components/charts';
import {
  DataTable,
  Grid2,
  Notice,
  Panel,
  RangeFields,
  RunButton,
  Toolbar,
  ViewStatus,
} from '@/components/workspace';
import { apiErrorMessage, useBenchmark, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { useIsMultiAsset } from '@/hooks/useProfile';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { WorkspacePayload } from '@/types/workspace';
import { RequireUniverse } from '../shared/Guards';

/** Current Portfolio > P&L > P&L Analysis */
const PnLAnalysisPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const setHistoricalEnabled = useWorkspaceStore((s) => s.setHistoricalEnabled);
  const params = useWorkspacePayload('expost', pnlFrequency, true);

  const view = useView('pnl-analysis', params, async (payload: WorkspacePayload) => {
    const response = await workspaceService.pnlAnalysis(payload);
    // 'Historical Portfolio' becomes available to the other tabs, as after the notebook's 'Get P&L'
    setHistoricalEnabled(true);
    return response;
  });

  const multiAsset = useIsMultiAsset();
  const benchmark = useBenchmark();
  const upload = useMutation({ mutationFn: workspaceService.upload });
  const onUpload = () => {
    const question = multiAsset
      ? "Add today's holdings (and missed days) to Quantities2 / Positions2 and push them to the GitHub repository?"
      : 'Push Positions, Quantities and the trade history to the GitHub repository?';
    if (window.confirm(question)) upload.mutate();
  };

  const data = view.data;
  const dailyColumns = data?.daily_pnl.columns.filter((c) => c !== 'Total');

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="expost" />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get P&L
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <>
          <p className="text-xs text-muted-foreground">
            Position history available from {data.history_start}.
          </p>
          <Grid2>
            <FrameChart frame={data.positions} title="Portfolio Value" visible={['Total']} />
            <FrameChart
              frame={data.cumulative_return}
              title="Cumulative Return"
              visible={['Historical Portfolio', 'Fund', benchmark.label]}
            />
            <FrameChart
              frame={data.cumulative_contribution}
              title="Cumulative P&L Contribution"
              visible={['Cumulative P&L']}
            />
            <FrameChart
              frame={data.daily_pnl}
              title="Daily P&L"
              kind="bar"
              barmode="relative"
              visible={dailyColumns}
            />
          </Grid2>
          <DataTable
            frame={data.daily_pnl}
            title="Daily P&L Contribution"
            format="currency"
            indexLabel="Date"
          />
          <Toolbar>
            <RunButton variant="secondary" onClick={onUpload} loading={upload.isPending}>
              {multiAsset ? 'Update Files' : 'Upload Files'}
            </RunButton>
          </Toolbar>
          {upload.error && <Notice tone="error">{apiErrorMessage(upload.error)}</Notice>}
          {upload.data && (
            <Notice tone="info">
              ✅ Uploaded:{' '}
              {Object.entries(upload.data.data.files)
                .map(([file, status]) => `${file}.xlsx (${status})`)
                .join(', ')}
            </Notice>
          )}
          {upload.data?.data.messages?.map((message) => (
            <Notice key={message} tone="info">
              {message}
            </Notice>
          ))}
        </>
      )}
    </Panel>
  );
};

const PnLAnalysis = () => (
  <RequireUniverse>
    <PnLAnalysisPage />
  </RequireUniverse>
);

export default PnLAnalysis;
