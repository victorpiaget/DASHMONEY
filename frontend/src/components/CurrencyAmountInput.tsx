import { useCurrency, SUPPORTED_CURRENCIES } from '../context/CurrencyContext'

interface Props {
  value: string
  onChange: (value: string) => void
  inputCurrency: string
  onCurrencyChange: (currency: string) => void
  /** Devise dans laquelle le montant sera stocké (devise native du compte / instrument). */
  nativeCurrency: string
  required?: boolean
  min?: string
  step?: string
  placeholder?: string
  autoFocus?: boolean
}

export function CurrencyAmountInput({
  value,
  onChange,
  inputCurrency,
  onCurrencyChange,
  nativeCurrency,
  required,
  min,
  step,
  placeholder,
  autoFocus,
}: Props) {
  const { convertBetween } = useCurrency()

  const isDifferent = inputCurrency !== nativeCurrency
  const nativeMeta = SUPPORTED_CURRENCIES.find((c) => c.code === nativeCurrency)
  const decimals = nativeMeta?.decimals ?? 2

  const converted =
    isDifferent && value !== '' && !isNaN(parseFloat(value))
      ? convertBetween(parseFloat(value), inputCurrency, nativeCurrency)
      : null

  return (
    <div>
      <div className="flex">
        <input
          type="number"
          required={required}
          min={min}
          step={step}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoFocus={autoFocus}
          className="flex-1 min-w-0 px-3.5 py-2.5 rounded-l-lg border border-gray-200 border-r-0 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition bg-white"
        />
        <select
          value={inputCurrency}
          onChange={(e) => onCurrencyChange(e.target.value)}
          className="px-2.5 py-2.5 rounded-r-lg border border-gray-200 bg-gray-50 text-xs font-medium text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-900 transition cursor-pointer"
        >
          {SUPPORTED_CURRENCIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.code}
            </option>
          ))}
        </select>
      </div>
      {converted !== null && (
        <p className="text-[10px] text-gray-400 mt-1 tabular-nums">
          ≈ {converted.toFixed(decimals)} {nativeCurrency}
        </p>
      )}
    </div>
  )
}
