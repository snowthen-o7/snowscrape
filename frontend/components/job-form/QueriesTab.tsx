'use client';

import { Controller, useFieldArray, useFormContext } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
import { Switch } from '@snowforge/ui';
import { Plus, Trash2 } from 'lucide-react';
import { QueryTypeHelpButton } from '@/components/QueryTypeHelp';
import { toast } from '@/lib/toast';
import type { JobFormValues } from '@/lib/schemas/jobFormSchema';

interface QueriesTabProps {
  queryErrors: (string | null)[];
}

const MAX_QUERIES = 10;

export function QueriesTab({ queryErrors }: QueriesTabProps) {
  const { control, watch, register, formState: { errors } } = useFormContext<JobFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: 'queries' });

  const handleAddQuery = () => {
    if (fields.length >= MAX_QUERIES) {
      toast.error('Maximum of 10 queries allowed');
      return;
    }
    const queries = watch('queries');
    const hasBlankQuery = queries.some(q => !q.name || !q.query);
    if (hasBlankQuery) {
      toast.error('Please fill out all query fields before adding a new one.');
      return;
    }
    append({ name: '', type: 'xpath', query: '', join: false });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Data Queries</CardTitle>
            <CardDescription>Define queries to extract data from HTML, JSON, or PDF content</CardDescription>
          </div>
          <QueryTypeHelpButton />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {fields.map((field, index) => (
          <div key={field.id} className="p-4 border rounded-lg space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Query {index + 1}</span>
              {fields.length > 1 && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => remove(index)}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor={`queryName-${index}`}>Field Name</Label>
                <Input
                  id={`queryName-${index}`}
                  placeholder="e.g., title, price, description"
                  {...register(`queries.${index}.name`)}
                />
                {errors.queries?.[index]?.name && (
                  <p className="text-sm text-destructive">{errors.queries[index].name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`queryType-${index}`}>Query Type</Label>
                <Controller
                  control={control}
                  name={`queries.${index}.type`}
                  render={({ field: typeField }) => (
                    <Select value={typeField.value} onValueChange={typeField.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="xpath">XPath (HTML)</SelectItem>
                        <SelectItem value="regex">Regex (Text)</SelectItem>
                        <SelectItem value="jsonpath">JSONPath (JSON)</SelectItem>
                        <SelectItem value="pdf_table">PDF Table</SelectItem>
                        <SelectItem value="pdf_text">PDF Text</SelectItem>
                        <SelectItem value="pdf_metadata">PDF Metadata</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="md:col-span-2 space-y-2">
                <Label htmlFor={`queryExpression-${index}`}>
                  {watch(`queries.${index}.type`)?.startsWith('pdf_') ? 'Expression (Optional)' : 'Expression'}
                </Label>
                <Input
                  id={`queryExpression-${index}`}
                  placeholder={
                    watch(`queries.${index}.type`) === 'xpath' ? '//div[@class="price"]/text()' :
                    watch(`queries.${index}.type`) === 'regex' ? '\\$([\\d.]+)' :
                    watch(`queries.${index}.type`) === 'jsonpath' ? '$.data.price' :
                    watch(`queries.${index}.type`) === 'pdf_table' ? 'Column name to extract (optional)' :
                    watch(`queries.${index}.type`) === 'pdf_text' ? 'Regex pattern to apply (optional)' :
                    ''
                  }
                  {...register(`queries.${index}.query`)}
                />
                {watch(`queries.${index}.type`) === 'pdf_table' && (
                  <p className="text-xs text-muted-foreground">
                    Leave empty to extract all columns. Enter a column name to extract only that column.
                  </p>
                )}
                {watch(`queries.${index}.type`) === 'pdf_text' && (
                  <p className="text-xs text-muted-foreground">
                    Leave empty to extract all text. Enter a regex pattern to extract specific data.
                  </p>
                )}
                {watch(`queries.${index}.type`) === 'pdf_metadata' && (
                  <p className="text-xs text-muted-foreground">
                    Extracts PDF metadata (title, author, page count, etc.)
                  </p>
                )}
                {queryErrors[index] && <p className="text-sm text-destructive">{queryErrors[index]}</p>}
              </div>
              <div className="flex items-center space-x-2">
                <Controller
                  control={control}
                  name={`queries.${index}.join`}
                  render={({ field: joinField }) => (
                    <Switch
                      id={`join-${index}`}
                      checked={!!joinField.value}
                      onCheckedChange={joinField.onChange}
                    />
                  )}
                />
                <Label htmlFor={`join-${index}`}>Join multiple results</Label>
              </div>
            </div>
          </div>
        ))}
        {fields.length < MAX_QUERIES && (
          <Button onClick={handleAddQuery} variant="outline" className="w-full">
            <Plus className="h-4 w-4 mr-2" />
            Add Query
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
