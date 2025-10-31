import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Code2, FileCode, Loader2 } from "lucide-react";

interface Pattern {
  id: string;
  name: string;
  description: string;
}

export function Text2CodePage() {
  const [sourceType, setSourceType] = useState<"volume" | "jira">("volume");
  const [volumePath, setVolumePath] = useState("");
  const [selectedPattern, setSelectedPattern] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [generatedCode, setGeneratedCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);

  // Fetch patterns on component mount
  useEffect(() => {
    fetchPatterns();
  }, []);

  const fetchPatterns = async () => {
    try {
      const response = await fetch("/api/code/patterns");
      const data = await response.json();
      setPatterns(data.patterns || []);
      // Set default pattern
      if (data.patterns && data.patterns.length > 0) {
        setSelectedPattern(data.patterns[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch patterns:", err);
    }
  };

  const handleGenerate = async () => {
    setError(null);
    setGeneratedCode("");

    // Validation
    if (sourceType === "volume" && !volumePath.trim()) {
      setError("Please enter a Volume path");
      return;
    }

    if (!selectedPattern) {
      setError("Please select a pattern");
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch("/api/code/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_type: sourceType,
          volume_path: sourceType === "volume" ? volumePath : null,
          pattern: selectedPattern,
          custom_prompt: customPrompt.trim() || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate code");
      }

      const data = await response.json();
      setGeneratedCode(data.code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(generatedCode);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100 flex items-center justify-center gap-2">
            <Code2 className="h-10 w-10" />
            Text2Code Generator
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Generate production-ready PySpark ETL code from mapping specifications
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Panel */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
              <CardDescription>Configure your data source and ETL pattern</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Source Type Tabs */}
              <div>
                <Label>Data Source</Label>
                <Tabs value={sourceType} onValueChange={(v) => setSourceType(v as "volume" | "jira")} className="mt-2">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="volume">Unity Catalog Volume</TabsTrigger>
                    <TabsTrigger value="jira">JIRA (Coming Soon)</TabsTrigger>
                  </TabsList>

                  <TabsContent value="volume" className="space-y-4 mt-4">
                    <div>
                      <Label htmlFor="volume-path">Volume Path</Label>
                      <Input
                        id="volume-path"
                        placeholder="/Volumes/catalog/schema/volume/input/mapping.csv"
                        value={volumePath}
                        onChange={(e) => setVolumePath(e.target.value)}
                        className="mt-2"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Enter the full path to your mapping CSV in Unity Catalog Volume
                      </p>
                    </div>
                  </TabsContent>

                  <TabsContent value="jira" className="mt-4">
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        JIRA integration is currently under development. Please use the Volume option for now.
                      </AlertDescription>
                    </Alert>
                  </TabsContent>
                </Tabs>
              </div>

              {/* Pattern Selection */}
              <div>
                <Label htmlFor="pattern">ETL Pattern</Label>
                <Select value={selectedPattern} onValueChange={setSelectedPattern}>
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select a pattern" />
                  </SelectTrigger>
                  <SelectContent>
                    {patterns.map((pattern) => (
                      <SelectItem key={pattern.id} value={pattern.id}>
                        <div>
                          <div className="font-medium">{pattern.name}</div>
                          <div className="text-xs text-slate-500">{pattern.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Custom Prompt (Optional) */}
              <div>
                <Label htmlFor="custom-prompt">Custom Prompt Template (Optional)</Label>
                <Textarea
                  id="custom-prompt"
                  placeholder="Enter a custom prompt template to override the default pattern..."
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  className="mt-2 min-h-[100px] font-mono text-sm"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Leave blank to use the default prompt for the selected pattern
                </p>
              </div>

              {/* Error Display */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Generate Button */}
              <Button onClick={handleGenerate} disabled={isLoading} className="w-full" size="lg">
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating Code...
                  </>
                ) : (
                  <>
                    <FileCode className="mr-2 h-4 w-4" />
                    Generate Code
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Code Preview Panel */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Generated Code</CardTitle>
              <CardDescription>Production-ready PySpark ETL code</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {generatedCode ? (
                <>
                  <div className="flex justify-end">
                    <Button onClick={handleCopyCode} variant="outline" size="sm">
                      Copy Code
                    </Button>
                  </div>
                  <div className="bg-slate-950 rounded-lg p-4 overflow-auto max-h-[600px]">
                    <pre className="text-sm text-slate-100 font-mono">
                      <code>{generatedCode}</code>
                    </pre>
                  </div>
                </>
              ) : (
                <div className="bg-slate-100 dark:bg-slate-800 rounded-lg p-12 text-center">
                  <Code2 className="h-16 w-16 mx-auto text-slate-400 mb-4" />
                  <p className="text-slate-600 dark:text-slate-400">
                    {isLoading
                      ? "Generating your PySpark code..."
                      : "Configure your source and pattern, then click Generate Code"}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Features Info */}
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>About Text2Code Generator</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <h4 className="font-semibold mb-2">🚀 Fast Development</h4>
                <p className="text-slate-600 dark:text-slate-400">
                  Generate production-ready PySpark ETL pipelines in seconds instead of hours
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">✨ Best Practices</h4>
                <p className="text-slate-600 dark:text-slate-400">
                  Generated code follows Databricks best practices for Unity Catalog and Delta Lake
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-2">🎯 Customizable</h4>
                <p className="text-slate-600 dark:text-slate-400">
                  Use predefined patterns or create your own custom prompt templates
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
