import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2, Code2, FileCode, FolderOpen, Loader2 } from "lucide-react";

interface Step {
  name: string;
  status: "pending" | "in_progress" | "completed" | "error";
  message?: string;
}

type WizardStep = "source" | "paths" | "pattern" | "generating" | "complete";

export function CodeGeneratorWizard() {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>("source");

  // Form data
  const [sourceType, setSourceType] = useState<"volume" | "jira" | null>(null);
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [pattern] = useState("pyspark");

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progressSteps, setProgressSteps] = useState<Step[]>([]);
  const [generatedCode, setGeneratedCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Step 1: Source Selection
  const handleSourceSelection = (type: "volume" | "jira") => {
    if (type === "jira") {
      setError("JIRA integration is work in progress. Please select Volume source.");
      return;
    }
    setSourceType(type);
    setError(null);
    setCurrentStep("paths");
  };

  // Step 2: Path Configuration
  const handlePathSubmit = () => {
    if (!inputPath.trim()) {
      setError("Please enter the input volume path");
      return;
    }
    if (!outputPath.trim()) {
      setError("Please enter the output volume path");
      return;
    }
    setError(null);
    setCurrentStep("pattern");
  };

  // Step 3: Pattern Selection (auto-proceed since we only have PySpark)
  const handlePatternSelection = () => {
    setCurrentStep("generating");
    generateCode();
  };

  // Step 4: Generate Code
  const generateCode = async () => {
    setIsGenerating(true);
    setError(null);
    setProgressSteps([]);

    try {
      const response = await fetch("/api/codegen/generate-pyspark", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_type: sourceType,
          input_volume_path: inputPath,
          output_volume_path: outputPath,
          pattern: pattern,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate code");
      }

      const data = await response.json();
      setProgressSteps(data.steps);
      setGeneratedCode(data.code);
      setCurrentStep("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setCurrentStep("pattern"); // Go back to allow retry
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(generatedCode);
  };

  const handleStartOver = () => {
    setCurrentStep("source");
    setSourceType(null);
    setInputPath("");
    setOutputPath("");
    setGeneratedCode("");
    setProgressSteps([]);
    setError(null);
  };

  // Render step progress indicator
  const stepLabels = ["Source", "Paths", "Pattern", "Generate"];
  const stepIndex = {
    source: 0,
    paths: 1,
    pattern: 2,
    generating: 3,
    complete: 3,
  }[currentStep];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100 flex items-center justify-center gap-2">
            <Code2 className="h-10 w-10" />
            PySpark Code Generator
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Transform mapping documents into production-ready PySpark code
          </p>
        </div>

        {/* Step Progress Indicator */}
        <div className="flex items-center justify-center gap-2">
          {stepLabels.map((label, idx) => (
            <div key={label} className="flex items-center">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full font-semibold ${
                  idx < stepIndex
                    ? "bg-green-500 text-white"
                    : idx === stepIndex
                    ? "bg-blue-500 text-white"
                    : "bg-slate-300 text-slate-600"
                }`}
              >
                {idx < stepIndex ? <CheckCircle2 className="h-5 w-5" /> : idx + 1}
              </div>
              <span className="ml-2 text-sm font-medium">{label}</span>
              {idx < stepLabels.length - 1 && <div className="w-12 h-0.5 bg-slate-300 mx-2" />}
            </div>
          ))}
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Step 1: Source Selection */}
        {currentStep === "source" && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Step 1: Select Data Source</CardTitle>
              <CardDescription>Choose where your mapping document is located</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  onClick={() => handleSourceSelection("volume")}
                  variant="outline"
                  className="h-32 flex flex-col gap-2 border-2 hover:border-blue-500"
                >
                  <FolderOpen className="h-12 w-12" />
                  <span className="text-lg font-semibold">Unity Catalog Volume</span>
                  <span className="text-xs text-slate-500">Read from UC Volume path</span>
                </Button>

                <Button
                  onClick={() => handleSourceSelection("jira")}
                  variant="outline"
                  className="h-32 flex flex-col gap-2 border-2 hover:border-blue-500 relative"
                >
                  <FileCode className="h-12 w-12" />
                  <span className="text-lg font-semibold">JIRA</span>
                  <span className="text-xs text-slate-500">Import from JIRA ticket</span>
                  <span className="absolute top-2 right-2 bg-yellow-500 text-white text-xs px-2 py-1 rounded">
                    WIP
                  </span>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Path Configuration */}
        {currentStep === "paths" && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Step 2: Configure Volume Paths</CardTitle>
              <CardDescription>Specify input mapping CSV and output code location</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="input-path">Input Volume Path (Mapping CSV)</Label>
                <Input
                  id="input-path"
                  placeholder="/Volumes/catalog/schema/volume/input/mapping_sheet.csv"
                  value={inputPath}
                  onChange={(e) => setInputPath(e.target.value)}
                />
                <p className="text-xs text-slate-500">
                  Full path to your mapping CSV file in Unity Catalog Volume
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="output-path">Output Volume Path (Generated Code)</Label>
                <Input
                  id="output-path"
                  placeholder="/Volumes/catalog/schema/volume/output/output.py"
                  value={outputPath}
                  onChange={(e) => setOutputPath(e.target.value)}
                />
                <p className="text-xs text-slate-500">
                  Where the generated PySpark code will be saved
                </p>
              </div>

              <div className="flex gap-2">
                <Button onClick={() => setCurrentStep("source")} variant="outline">
                  Back
                </Button>
                <Button onClick={handlePathSubmit} className="flex-1">
                  Next
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Pattern Selection */}
        {currentStep === "pattern" && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Step 3: Select ETL Pattern</CardTitle>
              <CardDescription>Choose the code generation pattern</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="border-2 border-blue-500 rounded-lg p-4 bg-blue-50 dark:bg-blue-900/20">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-6 w-6 text-blue-500 mt-1" />
                  <div>
                    <h3 className="font-semibold text-lg">PySpark ETL Pattern</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      Standard PySpark ETL with transformations and Delta write. Reads from source
                      volumes, applies column mappings and transformations, writes to target Delta
                      tables.
                    </p>
                    <div className="mt-2 text-xs text-slate-500">
                      ✓ Column transformations • ✓ Delta Lake writes • ✓ Error handling • ✓
                      Parameterization
                    </div>
                  </div>
                </div>
              </div>

              <Alert>
                <AlertDescription>
                  More patterns (MERGE, SCD Type 2) will be added in future releases.
                </AlertDescription>
              </Alert>

              <div className="flex gap-2">
                <Button onClick={() => setCurrentStep("paths")} variant="outline">
                  Back
                </Button>
                <Button onClick={handlePatternSelection} className="flex-1">
                  Generate Code
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Generating */}
        {currentStep === "generating" && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Step 4: Generating Code</CardTitle>
              <CardDescription>Please wait while we generate your PySpark code</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {progressSteps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  {step.status === "completed" && (
                    <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />
                  )}
                  {step.status === "in_progress" && (
                    <Loader2 className="h-5 w-5 text-blue-500 animate-spin flex-shrink-0" />
                  )}
                  {step.status === "error" && (
                    <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                  )}
                  {step.status === "pending" && (
                    <div className="h-5 w-5 border-2 border-slate-300 rounded-full flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <div className="font-medium">{step.name}</div>
                    {step.message && (
                      <div className="text-sm text-slate-500">{step.message}</div>
                    )}
                  </div>
                </div>
              ))}

              {isGenerating && (
                <div className="text-center text-slate-500">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
                  <p>Generating your PySpark code...</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 5: Complete */}
        {currentStep === "complete" && (
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-6 w-6 text-green-500" />
                Code Generated Successfully!
              </CardTitle>
              <CardDescription>Your PySpark ETL code is ready</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Progress Summary */}
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <h4 className="font-semibold mb-2">Generation Steps:</h4>
                {progressSteps.map((step, idx) => (
                  <div key={idx} className="text-sm flex items-center gap-2 mb-1">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>{step.name}</span>
                  </div>
                ))}
              </div>

              {/* Code Preview */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-semibold">Generated Code:</h4>
                  <Button onClick={handleCopyCode} variant="outline" size="sm">
                    Copy Code
                  </Button>
                </div>
                <div className="bg-slate-950 rounded-lg p-4 overflow-auto max-h-[500px]">
                  <pre className="text-sm text-slate-100 font-mono">
                    <code>{generatedCode}</code>
                  </pre>
                </div>
              </div>

              {/* Output Info */}
              <Alert>
                <AlertDescription>
                  Code has been generated and is ready to be saved to: <br />
                  <code className="bg-slate-200 dark:bg-slate-700 px-2 py-1 rounded mt-1 inline-block">
                    {outputPath}
                  </code>
                </AlertDescription>
              </Alert>

              <div className="flex gap-2">
                <Button onClick={handleStartOver} variant="outline" className="flex-1">
                  Generate Another
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
