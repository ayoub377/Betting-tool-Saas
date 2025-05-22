import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'marketValue',
  standalone: true
})
export class MarketValuePipe implements PipeTransform {
  transform(value: number): string {
    if (!value) {
      return 'N/A';
    }

    if (value >= 1_000_000) {
      return (value / 1_000_000).toFixed(2) + 'M €';
    } else if (value >= 1_000) {
      return (value / 1_000).toFixed(2) + 'K €';
    } else {
      return value.toFixed(2) + ' €';
    }
  }
}
