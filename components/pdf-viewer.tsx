"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Upload, FileText, X, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

declare global {
  interface Window {
    pdfjsLib: any
  }
}

export default function Component() {
  // PDF Viewer states
  const [pdfDoc, setPdfDoc] = useState<any>(null)
  const [pageNum, setPageNum] = useState(1)
  const [pageCount, setPageCount] = useState(0)
  const [fileName, setFileName] = useState<string>("")
  const [scale, setScale] = useState(1.5)
  const [loading, setLoading] = useState(false)

  // Backend integration states
  const [jsonData, setJsonData] = useState<any>(null)
  const [pdfUrl, setPdfUrl] = useState<string>("")
  const [uploading, setUploading] = useState(false)
  const [activeTab, setActiveTab] = useState("upload")

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const backendFileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Load PDF.js from CDN
    const script = document.createElement("script")
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"
    script.onload = () => {
      if (window.pdfjsLib) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
          "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"
      }
    }
    document.head.appendChild(script)

    return () => {
      document.head.removeChild(script)
    }
  }, [])

  // PDF Viewer functions
  const renderPage = async (pdf: any, pageNumber: number) => {
    const page = await pdf.getPage(pageNumber)
    const viewport = page.getViewport({ scale })
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext("2d")
    canvas.height = viewport.height
    canvas.width = viewport.width

    const renderContext = {
      canvasContext: context,
      viewport: viewport,
    }

    await page.render(renderContext).promise
  }

  const handleLocalFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || file.type !== "application/pdf") return

    setLoading(true)
    setFileName(file.name)

    try {
      const arrayBuffer = await file.arrayBuffer()
      const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise
      setPdfDoc(pdf)
      setPageCount(pdf.numPages)
      setPageNum(1)
      await renderPage(pdf, 1)
      setActiveTab("viewer")
    } catch (error) {
      console.error("Error loading PDF:", error)
    } finally {
      setLoading(false)
    }
  }

  // Backend integration functions
  const handleBackendUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await fetch("http://localhost:8000/upload-resume", {
        method: "POST",
        body: formData,
        mode: "cors", // Explicitly set CORS mode
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      const data = await res.json()
      setJsonData(data.json)
      setPdfUrl(`http://localhost:8000${data.pdf_url}`)
      setActiveTab("results")
    } catch (error) {
      console.error("Error uploading file:", error)

      // Show user-friendly error message
      if (error.message === "Failed to fetch") {
        alert(`CORS Error: Cannot connect to backend at localhost:8000. 
        
Please ensure:
1. Your backend server is running on port 8000
2. Your backend has CORS enabled for localhost:3000
3. Add these headers to your FastAPI/Flask backend:
   - Access-Control-Allow-Origin: http://localhost:3000
   - Access-Control-Allow-Methods: POST, GET, OPTIONS
   - Access-Control-Allow-Headers: Content-Type`)
      } else {
        alert(`Upload failed: ${error.message}`)
      }
    } finally {
      setUploading(false)
    }
  }

  const testBackendConnection = async () => {
    try {
      const res = await fetch("http://localhost:8000/", {
        method: "GET",
        mode: "cors",
      })
      if (res.ok) {
        alert("✅ Backend connection successful!")
      } else {
        alert(`❌ Backend responded with status: ${res.status}`)
      }
    } catch (error) {
      alert(`❌ Cannot connect to backend: ${error.message}
      
  Make sure:
  1. Backend is running on localhost:8000
  2. CORS is properly configured`)
    }
  }

  const goToPage = async (newPageNum: number) => {
    const pdfDocLocal = pdfDoc
    const pageCountLocal = pageCount
    if (!pdfDocLocal || newPageNum < 1 || newPageNum > pageCountLocal) return
    setPageNum(newPageNum)
    await renderPage(pdfDocLocal, newPageNum)
  }

  const changeScale = async (newScale: number) => {
    const pdfDocLocal = pdfDoc
    const pageNumLocal = pageNum
    if (!pdfDocLocal || newScale < 0.5 || newScale > 3) return
    setScale(newScale)
    await renderPage(pdfDocLocal, pageNumLocal)
  }

  const clearLocalPdf = () => {
    setPdfDoc(null)
    setPageNum(1)
    setPageCount(0)
    setFileName("")
    setScale(1.5)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const clearBackendData = () => {
    setJsonData(null)
    setPdfUrl("")
    if (backendFileInputRef.current) {
      backendFileInputRef.current.value = ""
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PDF Viewer & Resume Processor</h1>
          <p className="text-gray-600">Upload PDFs to view locally or process resumes with backend API</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="upload">Upload & Process</TabsTrigger>
            <TabsTrigger value="viewer">PDF Viewer</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Local PDF Viewer Upload */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Local PDF Viewer
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-4">View PDF files locally in browser</p>
                    <Button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={loading}
                      className="flex items-center gap-2"
                    >
                      <Upload className="w-4 h-4" />
                      {loading ? "Loading..." : "Choose PDF File"}
                    </Button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={handleLocalFileUpload}
                      className="hidden"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Backend Resume Processing */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Send className="w-5 h-5" />
                    Resume Processor
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
                    <Send className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-4">Upload resume to backend API for processing</p>
                    <div className="space-y-2">
                      <Button
                        onClick={() => backendFileInputRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-2"
                      >
                        <Upload className="w-4 h-4" />
                        {uploading ? "Processing..." : "Upload Resume"}
                      </Button>
                      <Button
                        onClick={testBackendConnection}
                        variant="outline"
                        size="sm"
                        className="flex items-center gap-2 bg-transparent"
                      >
                        Test Connection
                      </Button>
                    </div>
                    <input ref={backendFileInputRef} type="file" onChange={handleBackendUpload} className="hidden" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="viewer">
            {pdfDoc ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between bg-white p-4 rounded-lg shadow-sm border">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-gray-900">{fileName}</span>
                    <span className="text-sm text-gray-500">
                      Page {pageNum} of {pageCount}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => goToPage(pageNum - 1)} disabled={pageNum <= 1}>
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => goToPage(pageNum + 1)}
                      disabled={pageNum >= pageCount}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => changeScale(scale - 0.25)}
                      disabled={scale <= 0.5}
                    >
                      <ZoomOut className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => changeScale(scale + 0.25)} disabled={scale >= 3}>
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearLocalPdf}
                      className="flex items-center gap-2 bg-transparent"
                    >
                      <X className="w-4 h-4" />
                      Clear
                    </Button>
                  </div>
                </div>

                <Card className="overflow-hidden">
                  <CardContent className="p-4 flex justify-center bg-gray-100">
                    <canvas ref={canvasRef} className="max-w-full shadow-lg bg-white" style={{ maxHeight: "80vh" }} />
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <FileText className="w-16 h-16 text-gray-400 mb-4" />
                  <p className="text-gray-600 mb-4">No PDF loaded</p>
                  <Button onClick={() => setActiveTab("upload")}>Go to Upload</Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="results">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* JSON Results */}
              <Card>
                <CardHeader>
                  <CardTitle>Parsed JSON Data</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-96 whitespace-pre-wrap">
                    {jsonData ? JSON.stringify(jsonData, null, 2) : "No data yet."}
                  </pre>
                  {jsonData && (
                    <Button variant="outline" size="sm" onClick={clearBackendData} className="mt-4 bg-transparent">
                      Clear Data
                    </Button>
                  )}
                </CardContent>
              </Card>

              {/* Generated PDF */}
              <Card>
                <CardHeader>
                  <CardTitle>Generated PDF</CardTitle>
                </CardHeader>
                <CardContent>
                  {pdfUrl ? (
                    <div className="bg-white border rounded-lg overflow-hidden">
                      <iframe
                        src={pdfUrl}
                        title="Generated PDF"
                        className="w-full h-96 border-0"
                        style={{ backgroundColor: "white" }}
                      />
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                      <FileText className="w-12 h-12 mb-4" />
                      <p>No PDF generated yet.</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
