import { create } from "zustand";
import type { IDocument } from "@/types";

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

interface DocumentsState {
  documents: IDocument[];
  selectedDocumentIds: string[];
  isLoadingDocuments: boolean;
  isUploading: boolean;
  uploadModalOpen: boolean;
  setDocuments: (docs: IDocument[]) => void;
  addDocument: (doc: IDocument) => void;
  updateDocument: (id: string, patch: Partial<IDocument>) => void;
  removeDocument: (id: string) => void;
  toggleDocumentSelection: (id: string) => void;
  setSelectedDocumentIds: (ids: string[]) => void;
  selectAllProcessedDocuments: () => void;
  clearDocumentSelection: () => void;
  setIsLoadingDocuments: (loading: boolean) => void;
  setIsUploading: (uploading: boolean) => void;
  setUploadModalOpen: (open: boolean) => void;
}

export const useDocumentsStore = create<DocumentsState>((set) => ({
  documents: SAMPLE_DOCUMENTS,
  selectedDocumentIds: ["doc-demo-1", "doc-demo-2"],
  isLoadingDocuments: false,
  isUploading: false,
  uploadModalOpen: false,

  setDocuments: (docs) =>
    set((state) => {
      const validIds = new Set(
        docs.filter((d) => d.status === "processed").map((d) => d.id)
      );
      const hadOnlyDemoSelection =
        state.selectedDocumentIds.length > 0 &&
        state.selectedDocumentIds.every((id) => id.startsWith("doc-demo-"));
      const filteredSelection = state.selectedDocumentIds.filter((id) =>
        validIds.has(id)
      );
      const nextSelection =
        filteredSelection.length > 0
          ? filteredSelection
          : hadOnlyDemoSelection
          ? Array.from(validIds)
          : [];
      return {
        documents: docs,
        selectedDocumentIds: nextSelection,
      };
    }),

  addDocument: (doc) =>
    set((state) => ({
      documents: [doc, ...state.documents.filter((item) => item.id !== doc.id)],
      selectedDocumentIds:
        doc.status === "processed" &&
        !state.selectedDocumentIds.includes(doc.id)
          ? [...state.selectedDocumentIds, doc.id]
          : state.selectedDocumentIds,
    })),

  updateDocument: (id, patch) =>
    set((state) => ({
      documents: state.documents.map((doc) =>
        doc.id === id ? { ...doc, ...patch } : doc
      ),
    })),

  removeDocument: (id) =>
    set((state) => ({
      documents: state.documents.filter((doc) => doc.id !== id),
      selectedDocumentIds: state.selectedDocumentIds.filter(
        (item) => item !== id
      ),
    })),

  toggleDocumentSelection: (id) =>
    set((state) => {
      const target = state.documents.find((d) => d.id === id);
      if (target && target.status !== "processed") {
        return state;
      }
      return {
        selectedDocumentIds: state.selectedDocumentIds.includes(id)
          ? state.selectedDocumentIds.filter((item) => item !== id)
          : [...state.selectedDocumentIds, id],
      };
    }),

  setSelectedDocumentIds: (ids) => set({ selectedDocumentIds: ids }),

  selectAllProcessedDocuments: () =>
    set((state) => ({
      selectedDocumentIds: state.documents
        .filter((d) => d.status === "processed")
        .map((d) => d.id),
    })),

  clearDocumentSelection: () => set({ selectedDocumentIds: [] }),

  setIsLoadingDocuments: (loading) => set({ isLoadingDocuments: loading }),
  setIsUploading: (uploading) => set({ isUploading: uploading }),
  setUploadModalOpen: (open) => set({ uploadModalOpen: open }),
}));
