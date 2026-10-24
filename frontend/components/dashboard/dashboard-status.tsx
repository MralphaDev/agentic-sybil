
type DashboardStatusProps = {
  message: string;
};

export default function DashboardStatus({
  message,
}: DashboardStatusProps) {
  if (!message) return null;

  return (
    <div
      role="alert"
      className="mb-6 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-950/30 p-4 text-sm text-red-200"
    >
      <span className="mt-0.5 font-semibold">!</span>
      <p className="break-words">{message}</p>
    </div>
  );
}
