import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { useDocumentsStore } from "@/features/documents/useDocuments";

export function WorkspacePreview() {
  const { uploadModalOpen, setUploadModalOpen } = useDocumentsStore();

  return (
    <>
      <WorkspaceLayout>
        <ChatWindow />
      </WorkspaceLayout>

      {/* DIALOG TẢI TÀI LIỆU MỚI TÍCH HỢP UPLOADDROPZONE ([SP5-02.1 & SP5-02.2]) */}
      <Dialog open={uploadModalOpen} onOpenChange={setUploadModalOpen}>
        <DialogHeader>
          <DialogTitle>Tải lên tài liệu mới (PDF / DOCX)</DialogTitle>
          <DialogDescription>
            Hỗ trợ tệp văn bản .pdf và .docx có dung lượng tối đa 20MB/tệp. Hệ
            thống sẽ tự động trích xuất văn bản, chia Chunk và lập chỉ mục vào
            ChromaDB.
          </DialogDescription>
        </DialogHeader>

        <UploadDropzone
          onUploadSuccess={() => setUploadModalOpen(false)}
          onCancel={() => setUploadModalOpen(false)}
        />
      </Dialog>
    </>
  );
}

export default function App() {
  return <WorkspacePreview />;
}
