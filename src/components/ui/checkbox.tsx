import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check, Minus } from "lucide-react";

interface CheckboxProps {
  id?: string;
  checked: boolean | "indeterminate";
  onCheckedChange: (checked: boolean) => void;
  "aria-label": string;
  disabled?: boolean;
}

export function Checkbox({
  checked,
  onCheckedChange,
  ...props
}: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      className="checkbox"
      checked={checked}
      onCheckedChange={(value) => onCheckedChange(value === true)}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="checkbox__indicator">
        {checked === "indeterminate" ? (
          <Minus aria-hidden="true" />
        ) : (
          <Check aria-hidden="true" />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
