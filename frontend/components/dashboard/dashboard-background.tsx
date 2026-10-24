
export default function DashboardBackground() {
  return (
    <>
      <video
        className="pointer-events-none fixed inset-0 h-full w-full object-cover opacity-[0.12]"
        src="/videos/bg.mp4"
        autoPlay
        muted
        loop
        playsInline
      />

      <div className="pointer-events-none fixed inset-0 bg-[#080809]/75" />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/70" />

      <div className="pointer-events-none fixed -left-40 top-20 h-96 w-96 rounded-full bg-red-800/10 blur-[120px]" />
      <div className="pointer-events-none fixed -right-40 top-1/3 h-96 w-96 rounded-full bg-orange-700/10 blur-[140px]" />
    </>
  );
}
