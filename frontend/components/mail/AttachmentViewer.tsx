import { FileText, Image, Archive, File, Download } from "lucide-react";
import { formatBytes } from "../../lib/utils";
import type { Attachment } from "../../types";

interface AttachmentViewerProps {
  attachments: Attachment[];
}

function iconForType(contentType: string): React.ElementType {
  if (contentType.startsWith("image/")) return Image;
  if (contentType === "application/pdf" || contentType.startsWith("text/")) return FileText;
  if (contentType.includes("zip") || contentType.includes("tar") || contentType.includes("gz")) return Archive;
  return File;
}

export function AttachmentViewer({ attachments }: AttachmentViewerProps) {
  if (attachments.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
        {attachments.length} Attachment{attachments.length !== 1 ? "s" : ""}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {attachments.map((att, i) => {
          const Icon = iconForType(att.content_type);
          return (
            <a
              key={i}
              href={att.url}
              download={att.filename}
              className="flex items-center gap-2 p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group"
            >
              {att.content_type.startsWith("image/") ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={att.url}
                  alt={att.filename}
                  className="w-10 h-10 object-cover rounded shrink-0"
                />
              ) : (
                <Icon className="w-10 h-10 text-indigo-400 shrink-0 p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded" />
              )}
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">{att.filename}</p>
                <p className="text-xs text-gray-400">{formatBytes(att.size)}</p>
              </div>
              <Download className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            </a>
          );
        })}
      </div>
    </div>
  );
}
