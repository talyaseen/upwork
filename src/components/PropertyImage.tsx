import Image from "next/image";
import type { Property } from "@/lib/types";
import { blurDataURL } from "@/lib/images";

interface Props {
  property: Property;
  sizes: string;
  priority?: boolean;
  className?: string;
  imageClassName?: string;
}

/**
 * A property's hero photo over a gradient + blur placeholder built from the
 * property's accent colours. The gradient sits behind the image, so if the
 * photo is ever unavailable the card still renders as an elegant gradient
 * rather than a broken image.
 */
export function PropertyImage({
  property,
  sizes,
  priority = false,
  className = "",
  imageClassName = "",
}: Props) {
  return (
    <div
      className={`overflow-hidden ${className}`}
      style={{
        backgroundImage: `linear-gradient(135deg, ${property.accent_from}, ${property.accent_to})`,
      }}
    >
      {property.image_url && (
        <Image
          src={property.image_url}
          alt={`${property.name}, ${property.destination}`}
          fill
          sizes={sizes}
          priority={priority}
          placeholder="blur"
          blurDataURL={blurDataURL(property.accent_from, property.accent_to)}
          className={`object-cover ${imageClassName}`}
        />
      )}
    </div>
  );
}
