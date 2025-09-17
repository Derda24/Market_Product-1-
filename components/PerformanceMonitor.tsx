import { useEffect, useState } from 'react';

interface PerformanceMetrics {
  loadTime: number;
  productCount: number;
  memoryUsage?: number;
}

interface PerformanceMonitorProps {
  productCount: number;
  isVisible?: boolean;
}

export const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({ 
  productCount, 
  isVisible = false 
}) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    loadTime: 0,
    productCount: 0,
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Measure page load time
      const loadTime = performance.now();
      setMetrics(prev => ({
        ...prev,
        loadTime,
        productCount,
      }));

      // Monitor memory usage if available
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        setMetrics(prev => ({
          ...prev,
          memoryUsage: memory.usedJSHeapSize / 1024 / 1024, // Convert to MB
        }));
      }
    }
  }, [productCount]);

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-black/80 text-white p-3 rounded-lg text-xs z-50">
      <div className="space-y-1">
        <div>Load Time: {metrics.loadTime.toFixed(0)}ms</div>
        <div>Products: {metrics.productCount}</div>
        {metrics.memoryUsage && (
          <div>Memory: {metrics.memoryUsage.toFixed(1)}MB</div>
        )}
      </div>
    </div>
  );
};
