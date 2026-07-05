export function formatPrice(value: number): string {
  return value.toLocaleString('zh-CN', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

export function formatPercent(value: number): string {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

export function formatUpdatedAt(value: string, locale: string = 'zh-CN', prefix: string = '更新'): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return `${prefix} ${date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}`;
}

export function formatLastUpdated(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) {
    return '刚刚更新';
  } else if (diffMins < 60) {
    return `${diffMins}分钟前更新`;
  } else if (diffMins < 1440) {
    const diffHours = Math.floor(diffMins / 60);
    return `${diffHours}小时前更新`;
  } else {
    const diffDays = Math.floor(diffMins / 1440);
    if (diffDays === 1) {
      return '昨天更新';
    }
    return `${diffDays}天前更新`;
  }
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

export function getScoreColor(score: number): string {
  if (score >= 75) return '#0F8B8D';
  if (score >= 60) return '#D97706';
  return '#DC2626';
}

export function getChangeColor(change: number): string {
  return change >= 0 ? '#0F8B8D' : '#DC2626';
}

export function getRiskColor(risk: string): string {
  switch (risk) {
    case 'low': return '#0F8B8D';
    case 'medium': return '#D97706';
    case 'high': return '#DC2626';
    default: return '#6B7280';
  }
}

export function translateSignal(signal: string, translations: Record<string, string>): string {
  return translations[signal] || signal;
}

export function translateRisk(risk: string, translations: Record<string, string>): string {
  return translations[risk] || risk;
}

export function translateAction(action: string, translations: Record<string, string>): string {
  return translations[action] || action;
}
