import * as React from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, BookOpenCheck } from "lucide-react";
import { CitationBadge } from "@/components/citations/CitationBadge";
import { SourceCard } from "@/components/citations/SourceCard";
import type { ICitationSource, IMessage } from "@/types";

interface MessageBubbleProps {
  message: IMessage;
  activeCitation: ICitationSource | null;
  onSelectCitation: (
    citation: ICitationSource,
    allSources?: ICitationSource[]
  ) => void;
}

const CITATION_TOKEN_REGEX = /(\[S\d+\])/gi;

/**
 * [SP5-04.1] Biến đổi các ký hiệu [S1], [S2]... trong văn bản trả lời của AI
 * thành các nút nhãn (CitationBadge) nổi bật có thể nhấn chuột vào.
 */
function renderTextWithInlineCitations(
  children: React.ReactNode,
  sources: ICitationSource[] | undefined,
  activeCitation: ICitationSource | null,
  onSelectCitation: (
    citation: ICitationSource,
    allSources?: ICitationSource[]
  ) => void
): React.ReactNode {
  if (!sources || sources.length === 0) {
    return children;
  }

  return React.Children.map(children, (child) => {
    if (typeof child !== "string") {
      return child;
    }

    const parts = child.split(CITATION_TOKEN_REGEX);
    if (parts.length === 1) {
      return child;
    }

    return parts.map((part, index) => {
      const match = /^\[(S\d+)\]$/i.exec(part);
      if (!match) {
        return part;
      }

      const sourceId = match[1].toUpperCase();
      const matchedSource = sources.find(
        (s) => s.source_id.toUpperCase() === sourceId
      );
      if (!matchedSource) {
        return part;
      }

      const isActive =
        activeCitation?.source_id === matchedSource.source_id &&
        activeCitation?.document_id === matchedSource.document_id;

      return (
        <CitationBadge
          key={`${sourceId}-${index}`}
          source={matchedSource}
          isActive={isActive}
          onClick={(src) => onSelectCitation(src, sources)}
        />
      );
    });
  });
}

/**
 * [SP5-03.2 & SP5-04.1 & SP5-04.2] Bong bóng tin nhắn phân biệt rõ:
 * - Người dùng (role === 'user'): căn phải, nền xanh #2563EB, chữ trắng.
 * - Trợ lý AI (role === 'assistant'): căn trái, hỗ trợ hiển thị Markdown,
 *   chuyển đổi [S1], [S2] thành CitationBadge tương tác ([SP5-04.1]),
 *   và hiển thị danh sách thẻ nguồn thu gọn SourceCard bên dưới ([SP5-04.2]).
 */
export function MessageBubble({
  message,
  activeCitation,
  onSelectCitation,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const sources = message.sources || [];

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-2.5">
        <div
          style={{ backgroundColor: "#2563EB" }}
          className="max-w-[82%] rounded-2xl rounded-tr-xs px-4 py-3 text-[15px] leading-[1.65] text-white shadow-xs"
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start justify-start gap-2.5">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-white shadow-2xs">
        <Bot className="h-4 w-4" />
      </div>

      <div className="max-w-[85%] rounded-2xl rounded-tl-xs border border-border-default bg-bg-app px-4 py-3.5 text-[15px] leading-[1.65] text-text-primary shadow-2xs">
        {/* Hiển thị nội dung Markdown chuẩn với thẻ [S1], [S2] tương tác ([SP5-04.1]) */}
        <div className="space-y-2.5 break-words">
          <ReactMarkdown
            components={{
              p: ({ children }) => (
                <p className="leading-[1.65] last:mb-0">
                  {renderTextWithInlineCitations(
                    children,
                    sources,
                    activeCitation,
                    onSelectCitation
                  )}
                </p>
              ),
              ul: ({ children }) => (
                <ul className="ml-5 list-disc space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="ml-5 list-decimal space-y-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="leading-[1.65]">
                  {renderTextWithInlineCitations(
                    children,
                    sources,
                    activeCitation,
                    onSelectCitation
                  )}
                </li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-text-primary">
                  {children}
                </strong>
              ),
              code: ({ children }) => (
                <code className="rounded-md bg-slate-200/80 px-1.5 py-0.5 font-mono text-xs text-text-primary">
                  {children}
                </code>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-primary pl-3 italic text-text-secondary">
                  {children}
                </blockquote>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* [SP5-04.2] Danh sách thẻ nguồn thu gọn (SourceCard) ngay bên dưới câu trả lời */}
        {sources.length > 0 && (
          <div className="mt-3.5 border-t border-border-default pt-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-muted">
              <BookOpenCheck className="h-3.5 w-3.5 text-primary" />
              <span>Nguồn tham khảo xác thực ({sources.length}):</span>
            </div>

            <div className="flex flex-wrap gap-2">
              {sources.map((src) => {
                const isSelectedSource =
                  activeCitation?.source_id === src.source_id &&
                  activeCitation?.document_id === src.document_id;
                return (
                  <SourceCard
                    key={`${src.source_id}-${src.document_id}-${src.chunk_index ?? 0}`}
                    source={src}
                    compact={true}
                    isSelected={isSelectedSource}
                    onClick={(clickedSource) =>
                      onSelectCitation(clickedSource, sources)
                    }
                  />
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
