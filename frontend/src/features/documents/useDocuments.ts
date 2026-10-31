import { create } from "zustand";
import type { IDocument } from "@/types";

interface DocumentsState {
  selectedDocumentIds: string[];
  toggleDocumentSelection: (id: string) => void;
  setSelectedDocumentIds: (ids: string[]) => void;
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  selectedDocumentIds: ["doc-demo-1"],
  toggleDocumentSelection: (id) =>
    set((state) => ({
      selectedDocumentIds: state.selectedDocumentIds.includes(id)
        ? state.selectedDocumentIds.filter((item) => item !== id)
        : [...state.selectedDocumentIds, id],
    })),
  setSelectedDocumentIds: (ids) => set({ selectedDocumentIds: ids }),
}));

export const SAMPLE_DOCUMENTS: IDocument[] = [
  {
    id: "doc-demo-1",
    filename: "Bo_luat_Lao_dong_2019.pdf",
    storage_path: "./storage/uploads/demo-1.pdf",
    file_type: "pdf",
    file_size: 2516582,
    status: "processed",
    chunk_count: 142,
    created_at: "2026-11-01T00:00:00Z",
  },
  {
    id: "doc-demo-2",
    filename: "Noi_quy_Cong_ty_2026.docx",
    storage_path: "./storage/uploads/demo-2.docx",
    file_type: "docx",
    file_size: 430080,
    status: "processed",
    chunk_count: 28,
    created_at: "2026-11-01T00:15:00Z",
  },
  {
    id: "doc-demo-3",
    filename: "Quy_che_Dao_tao_Tin_chi.pdf",
    storage_path: "./storage/uploads/demo-3.pdf",
    file_type: "pdf",
    file_size: 1843200,
    status: "processing",
    chunk_count: 0,
    created_at: "2026-11-01T00:30:00Z",
  },
];

