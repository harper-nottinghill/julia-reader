import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "White paper · Julia Reader",
  description:
    "Agentic reading as a progressive, inspectable loop — Chronicle output, lake metadata, validation.",
};

export default function WhitePaperLayout({ children }: { children: ReactNode }) {
  return children;
}
