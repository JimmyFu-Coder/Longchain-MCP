import { useState, useRef } from 'react';
import styles from './FileUpload.module.css';

function FileUpload({ onFileProcessed }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const fileInputRef = useRef(null);

  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
  ];

  const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt'];

  const validateFile = (file) => {
    const isValidType = allowedTypes.includes(file.type);
    const isValidExtension = allowedExtensions.some(ext =>
      file.name.toLowerCase().endsWith(ext)
    );

    if (!isValidType && !isValidExtension) {
      throw new Error(`Unsupported file type: ${file.name}. Please upload PDF, Word or TXT files.`);
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      throw new Error(`File too large: ${file.name}. File size cannot exceed 10MB.`);
    }

    return true;
  };

  const uploadFileToServer = async (file) => {
    const formData = new FormData();
    formData.append('files', file);

    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, 30000);

    try {
      // First upload the file
      const uploadResponse = await fetch('http://127.0.0.1:8000/api/files/upload', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: {}
      });

      clearTimeout(timeout);

      if (!uploadResponse.ok) {
        let errorDetails = '';
        try {
          const errorData = await uploadResponse.json();
          errorDetails = JSON.stringify(errorData, null, 2);
        } catch {
          const errorText = await uploadResponse.text().catch(() => 'Unknown error');
          errorDetails = errorText;
        }
        throw new Error(`Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}\n${errorDetails}`);
      }

      const uploadResult = await uploadResponse.json();

      // Extract file_path from the upload result structure
      const filePath = uploadResult.results[0]?.file_info?.file_path;
      if (!filePath) {
        throw new Error('Upload response missing file path');
      }

      // Then process the uploaded file
      const processResponse = await fetch('http://127.0.0.1:8000/api/files/process', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          file_path: filePath,
          chunk_size: 500,
          return_best: 3
        })
      });

      if (!processResponse.ok) {
        throw new Error(`Processing failed: ${processResponse.status} ${processResponse.statusText}`);
      }

      const processResult = await processResponse.json();

      // Format the response to match our expected structure
      return {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.name.split('.').pop().toUpperCase(),
        content: processResult.content || uploadResult.content || '',
        extractedAt: new Date().toLocaleString(),
        wordCount: (processResult.content || uploadResult.content || '').length,
        serverData: { upload: uploadResult, process: processResult }
      };
    } catch (error) {
      clearTimeout(timeout);
      if (error.name === 'AbortError') {
        throw new Error('Upload timeout - please check your connection and try again');
      }
      throw error;
    }
  };

  const processFiles = async (files) => {
    setProcessing(true);
    const newProcessedFiles = [];

    for (const file of files) {
      try {
        // Validate file before upload
        validateFile(file);

        // Upload file to server
        const processedFile = await uploadFileToServer(file);
        newProcessedFiles.push(processedFile);

        // Notify parent component
        if (onFileProcessed) {
          onFileProcessed(processedFile);
        }
      } catch (error) {
        alert(`Failed to upload ${file.name}: ${error.message}`);
      }
    }

    setUploadedFiles(prev => [...prev, ...newProcessedFiles]);
    setProcessing(false);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      processFiles(files);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      processFiles(files);
    }
  };

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={styles.fileUpload}>
      <div className={styles.uploadHeader}>
        <h3 className={styles.title}>📎 File Upload</h3>
        <span className={styles.supportedTypes}>Supports PDF, Word, TXT files</span>
      </div>

      <div
        className={`${styles.dropZone} ${dragActive ? styles.dragActive : ''} ${processing ? styles.processing : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !processing && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt"
          onChange={handleFileSelect}
          className={styles.fileInput}
        />

        {processing ? (
          <div className={styles.processingState}>
            <div className={styles.spinner}></div>
            <p>Uploading and processing files...</p>
          </div>
        ) : (
          <div className={styles.uploadPrompt}>
            <div className={styles.uploadIcon}>📄</div>
            <p className={styles.promptText}>
              Drag files here or <span className={styles.browseText}>click to select files</span>
            </p>
            <p className={styles.sizeLimit}>Maximum file size: 10MB</p>
          </div>
        )}
      </div>

      {uploadedFiles.length > 0 && (
        <div className={styles.fileList}>
          <h4 className={styles.listTitle}>Uploaded Files ({uploadedFiles.length})</h4>
          {uploadedFiles.map((file, index) => (
            <div key={index} className={styles.fileItem}>
              <div className={styles.fileInfo}>
                <div className={styles.fileName}>
                  <span className={styles.fileIcon}>
                    {file.fileType === 'PDF' ? '📕' :
                     file.fileType === 'DOCX' || file.fileType === 'DOC' ? '📘' : '📄'}
                  </span>
                  {file.fileName}
                </div>
                <div className={styles.fileMetadata}>
                  <span>{file.fileType}</span>
                  <span>{formatFileSize(file.fileSize)}</span>
                  <span>{file.wordCount} characters</span>
                  <span>{file.extractedAt}</span>
                </div>
                {file.content && (
                  <div className={styles.fileContent}>
                    <p>{file.content.substring(0, 150)}...</p>
                  </div>
                )}
              </div>
              <button
                onClick={() => removeFile(index)}
                className={styles.removeButton}
                title="Remove file"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FileUpload;