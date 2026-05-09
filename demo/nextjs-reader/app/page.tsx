import ChronicleExplorer from "@/components/ChronicleExplorer";

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--paper)]">
      <main className="mx-auto max-w-7xl px-6 py-8">
        <ChronicleExplorer basePath="/chronicle-dune" />
      </main>
    </div>
  );
}
