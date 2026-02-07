import { NextResponse } from 'next/server';
import { reportHealth } from '../../../lib/snowglobe';

export async function GET() {
  const startTime = Date.now();

  try {
    const responseTimeMs = Date.now() - startTime;

    // Report to Snowglobe (fire and forget)
    reportHealth('healthy', { responseTimeMs }).catch(() => {});

    return NextResponse.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    });
  } catch (error) {
    // Report failure to Snowglobe
    reportHealth('down', {
      error: error instanceof Error ? error.message : 'Health check failed',
    }).catch(() => {});

    return NextResponse.json(
      {
        status: 'error',
        error: error instanceof Error ? error.message : 'Health check failed',
        timestamp: new Date().toISOString(),
      },
      { status: 503 }
    );
  }
}
