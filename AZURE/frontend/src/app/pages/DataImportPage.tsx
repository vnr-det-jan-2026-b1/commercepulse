import { useState, useRef } from "react";
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2, BarChart3, List } from "lucide-react";
import * as xlsx from "xlsx";

export function DataImportPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [parsedData, setParsedData] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file: File) => {
    const validTypes = [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
      "application/vnd.ms-excel",
      "text/csv"
    ];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls|csv)$/)) {
      setError("Please upload a valid Excel (.xlsx, .xls) or CSV file.");
      return;
    }

    setFile(file);
    setError(null);
    setIsProcessing(true);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = xlsx.read(data, { type: "binary" });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        // Convert sheet to JSON
        const jsonData = xlsx.utils.sheet_to_json(worksheet, { defval: "" });
        
        if (jsonData.length > 0) {
          setColumns(Object.keys(jsonData[0] as object));
          setParsedData(jsonData);
        } else {
          setError("The uploaded file appears to be empty.");
        }
      } catch (err) {
        console.error(err);
        setError("Failed to parse the file. Ensure it's a valid spreadsheet.");
      } finally {
        setIsProcessing(false);
      }
    };
    
    reader.onerror = () => {
      setError("An error occurred while reading the file.");
      setIsProcessing(false);
    };

    reader.readAsArrayBuffer(file);
  };

  const triggerUpload = () => {
    inputRef.current?.click();
  };

  const resetUpload = () => {
    setFile(null);
    setParsedData([]);
    setColumns([]);
  };

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Data Import</h1>
          <p className="text-sm text-gray-600 mt-1">
            Upload and analyze your custom datasets instantly.
          </p>
        </div>
        {parsedData.length > 0 && (
          <button 
            onClick={resetUpload}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 font-medium transition-colors"
          >
            Upload New File
          </button>
        )}
      </div>

      {!file && (
        <div 
          className={`w-full max-w-3xl mx-auto mt-12 bg-white rounded-2xl border-2 border-dashed transition-all duration-200 ${
            dragActive ? "border-purple-500 bg-purple-50" : "border-gray-300 hover:border-purple-400"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mb-6">
              <Upload className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload your spreadsheet</h3>
            <p className="text-gray-500 mb-8 max-w-md">
              Drag and drop your Excel or CSV files here, or click to browse from your computer. We'll automatically process and analyze the data.
            </p>
            <input 
              ref={inputRef}
              type="file" 
              className="hidden" 
              accept=".xlsx,.xls,.csv" 
              onChange={handleChange} 
            />
            <button 
              onClick={triggerUpload}
              className="px-6 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 font-medium transition-colors shadow-sm"
            >
              Select File to Upload
            </button>

            {error && (
              <div className="mt-6 flex items-center gap-2 text-red-600 bg-red-50 px-4 py-3 rounded-lg text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
          </div>
        </div>
      )}

      {isProcessing && (
        <div className="w-full max-w-xl mx-auto mt-20 text-center">
          <div className="inline-block animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mb-4"></div>
          <p className="text-gray-600 font-medium">Analyzing document and extracting insights...</p>
        </div>
      )}

      {file && !isProcessing && parsedData.length > 0 && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          
          {/* Analysis Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
             <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center gap-4">
               <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
                 <FileSpreadsheet className="w-6 h-6" />
               </div>
               <div>
                 <p className="text-sm text-gray-500 font-medium">Filename</p>
                 <p className="text-lg font-semibold text-gray-900 truncate max-w-[200px]" title={file.name}>{file.name}</p>
               </div>
             </div>
             
             <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center gap-4">
               <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                 <List className="w-6 h-6" />
               </div>
               <div>
                 <p className="text-sm text-gray-500 font-medium">Records Extracted</p>
                 <p className="text-2xl font-semibold text-gray-900">{parsedData.length.toLocaleString()}</p>
               </div>
             </div>

             <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex items-center justify-between">
               <div className="flex items-center gap-4">
                 <div className="p-3 bg-green-50 text-green-600 rounded-xl">
                   <BarChart3 className="w-6 h-6" />
                 </div>
                 <div>
                   <p className="text-sm text-gray-500 font-medium">Data Dimensions</p>
                   <p className="text-lg font-semibold text-gray-900">{columns.length} columns</p>
                 </div>
               </div>
               <div className="flex items-center text-green-600 text-sm font-medium gap-1 bg-green-50 px-3 py-1 rounded-full">
                 <CheckCircle2 className="w-4 h-4" /> Validated
               </div>
             </div>
          </div>

          {/* Data Preview Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Data Preview</h3>
                <p className="text-sm text-gray-500 mt-1">Showing the first 10 recorded entries.</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50/80 border-b border-gray-200">
                  <tr>
                    {columns.map((col, idx) => (
                      <th key={idx} className="text-left px-6 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {parsedData.slice(0, 10).map((row, rowIdx) => (
                    <tr key={rowIdx} className="hover:bg-gray-50/50 transition-colors">
                      {columns.map((col, colIdx) => (
                        <td key={colIdx} className="px-6 py-4 text-sm text-gray-700 whitespace-nowrap max-w-[200px] truncate">
                          {row[col]?.toString() || "-"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
