"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkBreaks from "remark-breaks";
import rehypeKatex from "rehype-katex";

import { AdaptiveMarkdown } from "@/components/shared/adaptive-markdown";
import { MarkdownCode, MarkdownPre } from "@/components/shared/markdown-code";

type LinkProps = {
  children?: React.ReactNode;
  href?: string;
  ref?: React.Ref<HTMLAnchorElement>;
};

const MENTION_PATTERN = /(@[^\s@,.!?;:]+)/gu;

const ImgBlock = ({
  src,
  alt,
  ...props
}: React.DetailedHTMLProps<
  React.ImgHTMLAttributes<HTMLImageElement>,
  HTMLImageElement
>) => {
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} {...props} />;
};

function renderMentions(text: string): React.ReactNode[] {
  const tokens = text.split(MENTION_PATTERN);
  return tokens.map((token, index) => {
    if (MENTION_PATTERN.test(token)) {
      MENTION_PATTERN.lastIndex = 0;
      return (
        <span
          key={`${token}-${index}`}
          className="cursor-text select-text rounded-md border border-border bg-primary/10 px-1.5 py-0.5 text-sm font-semibold text-foreground"
        >
          {token}
        </span>
      );
    }
    MENTION_PATTERN.lastIndex = 0;
    return <React.Fragment key={`${token}-${index}`}>{token}</React.Fragment>;
  });
}

function renderMentionNodes(node: React.ReactNode): React.ReactNode {
  if (typeof node === "string") {
    return renderMentions(node);
  }

  if (Array.isArray(node)) {
    return node.map((child, index) => (
      <React.Fragment key={index}>{renderMentionNodes(child)}</React.Fragment>
    ));
  }

  if (!React.isValidElement(node)) {
    return node;
  }

  const element = node as React.ReactElement<{ children?: React.ReactNode }>;
  const children = React.Children.map(element.props.children, (child) =>
    renderMentionNodes(child),
  );

  return React.cloneElement(element, undefined, children);
}

function withMentionHighlight<T extends { children?: React.ReactNode }>(
  render: (props: T) => React.ReactElement,
) {
  return (props: T) =>
    render({
      ...props,
      children: React.Children.map(props.children, (child) =>
        renderMentionNodes(child),
      ),
    });
}

const markdownComponents = {
  pre: MarkdownPre,
  code: MarkdownCode,
  a: ({ children, href, ...props }: LinkProps) => (
    <a
      className="text-foreground underline underline-offset-4 decoration-muted-foreground/30 hover:decoration-foreground transition-colors"
      target="_blank"
      rel="noopener noreferrer"
      href={href}
      {...props}
    >
      {children}
    </a>
  ),
  h1: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-xl font-bold mb-4 mt-6 text-foreground">{children}</h1>
  )),
  h2: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-lg font-bold mb-3 mt-5 text-foreground">{children}</h2>
  )),
  h3: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-base font-bold mb-2 mt-4 text-foreground">
      {children}
    </h3>
  )),
  p: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <p>{children}</p>
  )),
  li: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <li>{children}</li>
  )),
  blockquote: withMentionHighlight(
    ({ children }: { children?: React.ReactNode }) => (
      <blockquote>{children}</blockquote>
    ),
  ),
  strong: withMentionHighlight(
    ({ children }: { children?: React.ReactNode }) => (
      <strong>{children}</strong>
    ),
  ),
  em: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <em>{children}</em>
  )),
  hr: () => <hr className="my-4 border-border" />,
  img: ImgBlock,
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-4 rounded-lg border border-border">
      <table className="w-full table-fixed border-collapse text-sm">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="bg-muted/50">{children}</thead>
  ),
  tbody: ({ children }: { children?: React.ReactNode }) => (
    <tbody className="divide-y divide-border">{children}</tbody>
  ),
  th: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <th className="border-b border-border px-4 py-3 text-left font-semibold text-foreground break-words">
      {children}
    </th>
  )),
  td: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <td className="border-b border-border px-4 py-3 text-foreground break-words">
      {children}
    </td>
  )),
};

export function ServerMessageContent({ content }: { content: string }) {
  return (
    <AdaptiveMarkdown className="prose prose-base dark:prose-invert w-full min-w-0 max-w-none overflow-hidden break-words break-all [&_pre]:whitespace-pre-wrap [&_pre]:break-words [&_code]:break-words [&_p]:break-words [&_p]:break-all [&_*]:break-words [&_*]:break-all">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </AdaptiveMarkdown>
  );
}
