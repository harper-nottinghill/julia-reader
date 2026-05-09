"use client";

import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const markdownComponents = {
  h1: (props: ComponentPropsWithoutRef<"h1">) => (
    <h1 className="mb-4 mt-2 scroll-mt-24 border-b border-stone-200 pb-3 text-3xl font-bold text-stone-900" {...props} />
  ),
  h2: (props: ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mb-3 mt-10 scroll-mt-24 text-xl font-semibold text-stone-900" {...props} />
  ),
  h3: (props: ComponentPropsWithoutRef<"h3">) => (
    <h3 className="mb-2 mt-8 text-lg font-semibold text-stone-800" {...props} />
  ),
  h4: (props: ComponentPropsWithoutRef<"h4">) => (
    <h4 className="mb-2 mt-6 text-base font-semibold text-stone-800" {...props} />
  ),
  p: (props: ComponentPropsWithoutRef<"p">) => (
    <p className="mb-4 text-sm leading-relaxed text-stone-700 md:text-base" {...props} />
  ),
  ul: (props: ComponentPropsWithoutRef<"ul">) => (
    <ul className="mb-4 list-disc space-y-1 pl-6 text-sm md:text-base" {...props} />
  ),
  ol: (props: ComponentPropsWithoutRef<"ol">) => (
    <ol className="mb-4 list-decimal space-y-1 pl-6 text-sm md:text-base" {...props} />
  ),
  li: (props: ComponentPropsWithoutRef<"li">) => <li className="text-stone-700" {...props} />,
  blockquote: (props: ComponentPropsWithoutRef<"blockquote">) => (
    <blockquote
      className="my-4 border-l-4 border-amber-600/70 bg-amber-50/60 py-2 pl-4 pr-2 text-stone-800 italic"
      {...props}
    />
  ),
  hr: () => <hr className="my-10 border-stone-200" />,
  table: (props: ComponentPropsWithoutRef<"table">) => (
    <div className="my-6 overflow-x-auto rounded-lg border border-stone-200">
      <table className="w-full min-w-[32rem] border-collapse text-left text-sm" {...props} />
    </div>
  ),
  thead: (props: ComponentPropsWithoutRef<"thead">) => <thead className="bg-stone-100" {...props} />,
  th: (props: ComponentPropsWithoutRef<"th">) => (
    <th className="border-b border-stone-200 px-3 py-2 font-semibold text-stone-900" {...props} />
  ),
  td: (props: ComponentPropsWithoutRef<"td">) => (
    <td className="border-b border-stone-100 px-3 py-2 text-stone-700" {...props} />
  ),
  tr: (props: ComponentPropsWithoutRef<"tr">) => <tr className="hover:bg-stone-50/80" {...props} />,
  code: ({
    className,
    children,
    ...rest
  }: ComponentPropsWithoutRef<"code"> & { className?: string }) => {
    const inline = !className;
    if (inline) {
      return (
        <code
          className="rounded bg-stone-200/90 px-1 py-0.5 font-mono text-[0.85em] text-stone-900"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code className={`font-mono text-xs ${className ?? ""}`} {...rest}>
        {children}
      </code>
    );
  },
  pre: (props: ComponentPropsWithoutRef<"pre">) => (
    <pre className="mb-4 overflow-x-auto rounded-lg bg-stone-100 p-4 text-xs text-stone-900" {...props} />
  ),
  a: (props: ComponentPropsWithoutRef<"a">) => (
    <a className="text-amber-800 underline decoration-amber-300 underline-offset-2 hover:text-amber-950" {...props} />
  ),
  strong: (props: ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-semibold text-stone-900" {...props} />
  ),
};

export function MarkdownBody({ markdown }: { markdown: string }) {
  return (
    <div className="max-w-none text-stone-900">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
