/**
 * Visual Scraper Builder
 * Point-and-click interface for building scraping jobs
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  MousePointer2,
  Code,
  Eye,
  Save,
  Play,
  AlertCircle,
  CheckCircle2,
  Trash2,
  Plus,
  Wand2,
} from 'lucide-react';
import { toast } from '@/lib/toast';

interface ExtractedField {
  id: string;
  name: string;
  selector: string;
  type: 'xpath' | 'css' | 'regex';
  value?: string;
  element?: string;
}

export default function VisualBuilderPage() {
  const router = useRouter();
  const [targetUrl, setTargetUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pageLoaded, setPageLoaded] = useState(false);
  const [extractedFields, setExtractedFields] = useState<ExtractedField[]>([]);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);

  // Sample page structure for demonstration
  const [pageStructure, setPageStructure] = useState<any>(null);

  const handleLoadPage = async () => {
    if (!targetUrl) {
      toast.error('Please enter a URL');
      return;
    }

    setIsLoading(true);

    try {
      // Simulate loading page structure
      // In production, this would make a request to a backend service that:
      // 1. Fetches the page
      // 2. Parses the DOM
      // 3. Returns a simplified structure with selectable elements

      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Mock page structure
      const mockStructure = {
        title: 'Sample E-commerce Product Page',
        elements: [
          {
            id: 'el-1',
            type: 'h1',
            text: 'Premium Wireless Headphones',
            xpath: '//h1[@class="product-title"]',
            css: '.product-title',
            path: 'body > div.container > h1.product-title',
          },
          {
            id: 'el-2',
            type: 'span',
            text: '$299.99',
            xpath: '//span[@class="price"]',
            css: '.price',
            path: 'body > div.container > div.product-info > span.price',
          },
          {
            id: 'el-3',
            type: 'div',
            text: '4.5 stars',
            xpath: '//div[@class="rating"]',
            css: '.rating',
            path: 'body > div.container > div.product-info > div.rating',
          },
          {
            id: 'el-4',
            type: 'p',
            text:
              'Premium noise-cancelling headphones with superior sound quality and long battery life...',
            xpath: '//p[@class="description"]',
            css: '.description',
            path: 'body > div.container > p.description',
          },
          {
            id: 'el-5',
            type: 'span',
            text: 'In Stock',
            xpath: '//span[@class="availability"]',
            css: '.availability',
            path: 'body > div.container > div.product-info > span.availability',
          },
        ],
      };

      setPageStructure(mockStructure);
      setPageLoaded(true);
      toast.success('Page loaded successfully');
    } catch (error) {
      console.error('Error loading page', error);
      toast.error('Failed to load page');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectElement = (element: any) => {
    setSelectedElement(element.id);

    // Auto-generate field name from element type and content
    const suggestedName = element.text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '_')
      .substring(0, 20) || element.type;

    // Check if this element is already added
    if (extractedFields.find((f) => f.selector === element.xpath)) {
      toast.info('This element is already added');
      return;
    }

    const newField: ExtractedField = {
      id: `field-${Date.now()}`,
      name: suggestedName,
      selector: element.xpath,
      type: 'xpath',
      value: element.text,
      element: `${element.type}: ${element.text.substring(0, 50)}...`,
    };

    setExtractedFields([...extractedFields, newField]);
    toast.success(`Added field: ${suggestedName}`);
  };

  const handleUpdateField = (fieldId: string, key: string, value: any) => {
    setExtractedFields(
      extractedFields.map((field) =>
        field.id === fieldId ? { ...field, [key]: value } : field
      )
    );
  };

  const handleRemoveField = (fieldId: string) => {
    setExtractedFields(extractedFields.filter((f) => f.id !== fieldId));
    toast.success('Field removed');
  };

  const handleTestExtraction = () => {
    // Simulate extraction
    const mockData = extractedFields.map((field) => ({
      [field.name]: field.value || 'Sample extracted value',
    }));

    setPreviewData(mockData);
    toast.success('Extraction test completed');
  };

  const handleSaveAsJob = () => {
    if (extractedFields.length === 0) {
      toast.error('Add at least one field to extract');
      return;
    }

    toast.success('Job created successfully');
    router.push('/dashboard');
  };

  const handleSaveAsTemplate = () => {
    if (extractedFields.length === 0) {
      toast.error('Add at least one field to extract');
      return;
    }

    const templateName = prompt('Enter a name for this template:');
    if (!templateName) return;

    toast.success(`Template "${templateName}" saved`);
  };

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Back Button */}
        <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>

        <PageHeader
          title="Visual Scraper Builder"
          description="Point and click to build your scraping job without writing code"
        />

        {/* URL Input */}
        <Card>
          <CardHeader>
            <CardTitle>Target Website</CardTitle>
            <CardDescription>
              Enter the URL of the page you want to scrape
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="https://example.com/product/123"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                className="flex-1"
                disabled={pageLoaded}
              />
              {!pageLoaded ? (
                <Button onClick={handleLoadPage} disabled={isLoading}>
                  {isLoading ? 'Loading...' : 'Load Page'}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={() => {
                    setPageLoaded(false);
                    setPageStructure(null);
                    setExtractedFields([]);
                    setPreviewData([]);
                  }}
                >
                  Change URL
                </Button>
              )}
            </div>

            {!pageLoaded && (
              <div className="mt-4 rounded-lg border border-blue-500 bg-blue-900/10 p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-blue-300 mb-1">How it works:</p>
                    <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                      <li>Enter the URL of the page you want to scrape</li>
                      <li>Click elements on the page to select them for extraction</li>
                      <li>Configure field names and selectors</li>
                      <li>Test the extraction to preview results</li>
                      <li>Save as a job or reusable template</li>
                    </ol>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {pageLoaded && pageStructure && (
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Page Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MousePointer2 className="h-5 w-5" />
                  Page Elements
                </CardTitle>
                <CardDescription>
                  Click on elements below to add them to your extraction
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="rounded-lg border border-border bg-muted/50 p-4 mb-4">
                    <h3 className="font-medium mb-2">{pageStructure.title}</h3>
                    <Badge variant="outline">Sample Page Structure</Badge>
                  </div>

                  {pageStructure.elements.map((element: any) => (
                    <div
                      key={element.id}
                      onClick={() => handleSelectElement(element)}
                      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                        selectedElement === element.id
                          ? 'border-brand-accent bg-brand-accent/10'
                          : 'border-border hover:border-brand-accent/50 hover:bg-brand-accent/5'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <Badge variant="secondary">{element.type}</Badge>
                        {extractedFields.find((f) => f.selector === element.xpath) && (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <p className="text-sm font-medium mb-1">{element.text}</p>
                      <code className="text-xs text-muted-foreground block truncate">
                        {element.xpath}
                      </code>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Extracted Fields Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  Extracted Fields ({extractedFields.length})
                </CardTitle>
                <CardDescription>
                  Configure the fields you want to extract
                </CardDescription>
              </CardHeader>
              <CardContent>
                {extractedFields.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <Wand2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium mb-2">No fields yet</p>
                    <p className="text-sm">
                      Click on elements in the page preview to add them
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {extractedFields.map((field) => (
                      <div
                        key={field.id}
                        className="rounded-lg border border-border p-4 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <Badge variant="outline">{field.type.toUpperCase()}</Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveField(field.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>

                        <div>
                          <Label htmlFor={`name-${field.id}`}>Field Name</Label>
                          <Input
                            id={`name-${field.id}`}
                            value={field.name}
                            onChange={(e) =>
                              handleUpdateField(field.id, 'name', e.target.value)
                            }
                            className="mt-1"
                          />
                        </div>

                        <div>
                          <Label htmlFor={`type-${field.id}`}>Selector Type</Label>
                          <Select
                            value={field.type}
                            onValueChange={(value) =>
                              handleUpdateField(field.id, 'type', value)
                            }
                          >
                            <SelectTrigger id={`type-${field.id}`} className="mt-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="xpath">XPath</SelectItem>
                              <SelectItem value="css">CSS Selector</SelectItem>
                              <SelectItem value="regex">Regex</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <Label htmlFor={`selector-${field.id}`}>Selector</Label>
                          <Input
                            id={`selector-${field.id}`}
                            value={field.selector}
                            onChange={(e) =>
                              handleUpdateField(field.id, 'selector', e.target.value)
                            }
                            className="mt-1 font-mono text-xs"
                          />
                        </div>

                        {field.value && (
                          <div className="rounded bg-muted p-2">
                            <p className="text-xs text-muted-foreground mb-1">Preview:</p>
                            <p className="text-sm">{field.value}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Preview & Actions */}
        {pageLoaded && extractedFields.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Extraction Preview
              </CardTitle>
              <CardDescription>
                Test your configuration to see the extracted data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button onClick={handleTestExtraction}>
                  <Play className="mr-2 h-4 w-4" />
                  Test Extraction
                </Button>
              </div>

              {previewData.length > 0 && (
                <div className="rounded-lg bg-muted p-4">
                  <pre className="text-xs overflow-x-auto">
                    {JSON.stringify(previewData, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Save Actions */}
        {pageLoaded && extractedFields.length > 0 && (
          <Card className="border-brand-accent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold mb-1">Save Your Configuration</h3>
                  <p className="text-sm text-muted-foreground">
                    Create a job or save as a reusable template
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleSaveAsTemplate}>
                    <Save className="mr-2 h-4 w-4" />
                    Save as Template
                  </Button>
                  <Button onClick={handleSaveAsJob}>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Create Job
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
